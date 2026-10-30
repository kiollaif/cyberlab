"""Связь чистой модели со снимками SQLite. Интерфейс вызывает только этот слой."""

from dataclasses import replace

from cyberlab.domain import ComputerState, Scenario, ScenarioNode
from cyberlab.scenarios import PHISHING
from cyberlab.storage import HistoryEntry, HistoryRepository


class LabSession:
    def __init__(self, repository: HistoryRepository, scenario: Scenario = PHISHING) -> None:
        self.repository = repository
        self.switch_scenario(scenario)

    def switch_scenario(self, scenario: Scenario) -> None:
        """Открыть последнюю тренировку выбранного сценария, не затрагивая остальные."""
        saved = self.repository.latest_session(scenario.id)
        session = saved or self.repository.create_session(
            scenario.id, scenario.start_node, ComputerState(events=(scenario.initial_event,))
        )
        active = self.repository.entry(session.active_entry_id, session.id)
        scenario.node(active.node_id)
        self.scenario, self.session, self.active = scenario, session, active

    @property
    def node(self) -> ScenarioNode:
        return self.scenario.node(self.active.node_id)

    @property
    def entries(self) -> list[HistoryEntry]:
        return self.repository.entries(self.session.id)

    def choose(self, choice_id: str) -> HistoryEntry:
        """Вычислить последствия, сохранить ребёнка текущего шага и перейти к нему."""
        next_node, next_state, selected_choice = self.scenario.advance(
            self.active.node_id, self.active.state, choice_id
        )
        # Сначала SQLite сохраняет снимок и указатель одной транзакцией.
        # Если запись не удалась, присваивание self.active не выполнится.
        self.active = self.repository.append(
            session_id=self.session.id,
            parent_id=self.active.id,
            choice_id=selected_choice.id,
            choice_title=selected_choice.title,
            node_id=next_node.id,
            state=next_state,
        )
        self.session = replace(self.session, active_entry_id=self.active.id)
        return self.active

    def go_to(self, entry_id: str) -> HistoryEntry:
        """Выбрать сохранённый снимок. Все его потомки остаются в истории."""
        self.active = self.repository.activate(self.session.id, entry_id)
        self.session = replace(self.session, active_entry_id=self.active.id)
        return self.active

    def new_session(self) -> None:
        self.session = self.repository.create_session(
            self.scenario.id,
            self.scenario.start_node,
            ComputerState(events=(self.scenario.initial_event,)),
        )
        self.active = self.repository.entry(self.session.active_entry_id, self.session.id)

    def open_session(self, session_id: str, *, scenario: Scenario | None = None) -> None:
        """Продолжить другую тренировку, сохранив обе истории и их указатели."""
        target_scenario = scenario if scenario is not None else self.scenario
        for saved_session in self.repository.sessions(target_scenario.id):
            if saved_session.id == session_id:
                saved_entry = self.repository.entry(saved_session.active_entry_id, session_id)
                target_scenario.node(saved_entry.node_id)
                # Проверяем данные до присваивания: ошибка не меняет текущую тренировку.
                self.scenario = target_scenario
                self.session = saved_session
                self.active = saved_entry
                return
        raise ValueError("Прохождение этого сценария не найдено.")
