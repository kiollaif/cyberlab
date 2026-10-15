"""Связь чистой модели со снимками SQLite. Интерфейс вызывает только этот слой."""

from dataclasses import replace

from cyberlab.domain import Scenario, ScenarioNode
from cyberlab.scenarios import PHISHING
from cyberlab.storage import HistoryEntry, HistoryRepository


class LabSession:
    def __init__(self, repository: HistoryRepository, scenario: Scenario = PHISHING) -> None:
        self.repository = repository
        self.scenario = scenario
        saved = repository.latest_session(scenario.id)
        self.session = saved or repository.create_session(scenario.id, scenario.start_node)
        self.active = repository.entry(self.session.active_entry_id, self.session.id)
        scenario.node(self.active.node_id)

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
        self.session = self.repository.create_session(self.scenario.id, self.scenario.start_node)
        self.active = self.repository.entry(self.session.active_entry_id, self.session.id)
