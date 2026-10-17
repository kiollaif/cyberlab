"""Экраны ситуации, последствия и итогов. Правила переходов остаются в модели."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QProgressBar, QVBoxLayout, QWidget

from cyberlab.domain import ComputerState, Scenario
from cyberlab.learning import (
    decision_rating,
    history_path,
    remaining_decisions,
    risk_level,
    state_summary,
)
from cyberlab.mentor import explain_decision, explain_state
from cyberlab.storage import HistoryEntry
from cyberlab.ui_helpers import action_button, clear_layout, create_label, create_panel


class StateOverview(QWidget):
    """Короткая сводка всегда видна; подробности доступны отдельной кнопкой."""

    def __init__(self, *, compact: bool = False) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.risk = create_label("", "heading")
        self.meter = QProgressBar()
        self.meter.setRange(0, 100)
        self.meter.setTextVisible(False)
        self.meter.setFixedHeight(10)
        self.status = create_label()
        layout.addWidget(self.risk)
        layout.addWidget(self.meter)
        layout.addWidget(self.status)
        explanation = create_label(
            "Учебный риск — условная шкала от 0 до 100, а не вероятность атаки. "
            "Чем выше значение, тем опаснее ситуация в сценарии.",
            "muted",
        )
        layout.addWidget(explanation)
        self.status.setVisible(not compact)
        explanation.setVisible(not compact)

    def render(self, state: ComputerState) -> None:
        self.risk.setText(f"Учебный риск: {state.risk} / 100 · {risk_level(state.risk)}")
        self.meter.setValue(state.risk)
        color = "#ed997a" if state.risk >= 60 else "#efc18e" if state.risk >= 25 else "#60e2bd"
        self.meter.setStyleSheet(f"QProgressBar::chunk {{ background: {color}; }}")
        password = "раскрыт" if state.credentials_exposed else "защищён"
        files = "недоступны" if state.files_encrypted else "доступны"
        network = "подключена" if state.network_connected else "отключена"
        self.status.setText(f"Учебный пароль: {password} · Файлы: {files} · Сеть: {network}")


class SituationPage(QWidget):
    choice_selected = Signal(str)
    details_requested = Signal()
    decisions_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self.progress_text = create_label("", "muted")
        layout.addWidget(self.progress_text)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        layout.addWidget(self.progress)
        self.stage = create_label("1. Ситуация → 2. Ваш выбор", "badge")
        layout.addWidget(self.stage)
        self.title = create_label("", "storyTitle")
        self.description = create_label()
        layout.addWidget(self.title)
        layout.addWidget(self.description)
        layout.addWidget(create_label("Как вы поступите?", "heading"))
        self.actions = QVBoxLayout()
        self.actions.setSpacing(10)
        layout.addLayout(self.actions)
        self.overview = StateOverview()
        layout.addWidget(self.overview)
        self.mentor_toggle = action_button("Подсказка наставника")
        self.mentor_toggle.setCheckable(True)
        self.mentor = create_label("", "badge")
        self.mentor.setVisible(False)
        self.mentor_toggle.toggled.connect(self.mentor.setVisible)
        layout.addWidget(self.mentor_toggle)
        layout.addWidget(self.mentor)
        controls = QHBoxLayout()
        self.details_button = action_button("Виртуальный компьютер", "Почта, файлы и журнал")
        self.decisions_button = action_button("Ваши решения", "Вернуться и попробовать иначе")
        self.details_button.clicked.connect(self.details_requested.emit)
        self.decisions_button.clicked.connect(self.decisions_requested.emit)
        controls.addWidget(self.details_button)
        controls.addWidget(self.decisions_button)
        layout.addLayout(controls)
        layout.addStretch()

    def render(self, scenario: Scenario, entries: list[HistoryEntry], active: HistoryEntry) -> None:
        node = scenario.node(active.node_id)
        made = len(history_path(entries, active.id)) - 1
        remaining = remaining_decisions(scenario, node.id)
        self.progress_text.setText(
            f"{scenario.title}\nПринято решений: {made} · До итога: не более {remaining}"
        )
        self.progress.setRange(0, max(1, made + remaining))
        self.progress.setValue(made)
        self.title.setText(node.title)
        self.description.setText(node.description)
        clear_layout(self.actions)
        for choice in node.choices:
            button = action_button(choice.title, choice.hint, primary=True)
            button.setObjectName(f"choice_{choice.id}")
            # Значение по умолчанию запоминает id именно этой кнопки цикла.
            button.clicked.connect(
                lambda _checked=False, choice_id=choice.id: self.choice_selected.emit(choice_id)
            )
            self.actions.addWidget(button)
        self.overview.render(active.state)
        self.mentor_toggle.setChecked(False)
        self.mentor.setText(explain_state(active.state))


class ConsequencePage(QWidget):
    continue_requested = Signal()
    details_requested = Signal()
    alternative_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(create_label("3. Последствие вашего решения", "badge"))
        self.action = create_label("", "storyTitle")
        layout.addWidget(self.action)
        panel, contents = create_panel("Что произошло")
        self.event = create_label()
        contents.addWidget(self.event)
        self.changes = create_label("", "badge")
        contents.addWidget(self.changes)
        contents.addWidget(create_label("Почему это произошло", "heading"))
        self.reason = create_label()
        contents.addWidget(self.reason)
        layout.addWidget(panel)
        self.risk_change = create_label("", "heading")
        layout.addWidget(self.risk_change)
        self.overview = StateOverview()
        layout.addWidget(self.overview)
        self.next_step = create_label()
        layout.addWidget(self.next_step)
        self.continue_button = action_button("Продолжить", primary=True)
        self.continue_button.setObjectName("continue_after_decision")
        self.continue_button.clicked.connect(self.continue_requested.emit)
        layout.addWidget(self.continue_button)
        controls = QHBoxLayout()
        self.details_button = action_button("Посмотреть на компьютере")
        self.alternative_button = action_button("Попробовать другой вариант")
        self.details_button.clicked.connect(self.details_requested.emit)
        self.alternative_button.clicked.connect(self.alternative_requested.emit)
        controls.addWidget(self.details_button)
        controls.addWidget(self.alternative_button)
        layout.addLayout(controls)
        layout.addStretch()

    def render(self, before: HistoryEntry, after: HistoryEntry, *, terminal: bool) -> None:
        self.action.setText(f"Вы выбрали: {after.choice_title}")
        self.event.setText(after.state.events[-1])
        self.reason.setText(explain_decision(after.choice_id, before.state, after.state))
        self.changes.setText(state_summary(after.state))
        difference = after.state.risk - before.state.risk
        change = f"{difference:+d}" if difference else "без изменения"
        self.risk_change.setText(f"Риск: {before.state.risk} → {after.state.risk} / 100 ({change})")
        self.overview.render(after.state)
        self.next_step.setText(
            "Ветка завершена. Нажмите «Продолжить», чтобы разобрать свои решения."
            if terminal
            else "Нажмите «Продолжить», чтобы перейти к следующей ситуации."
        )


class ResultsPage(QWidget):
    retry_requested = Signal()
    decisions_requested = Signal()
    compare_requested = Signal()
    menu_requested = Signal()
    details_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(create_label("4. Итоги прохождения", "badge"))
        self.title = create_label("", "storyTitle")
        self.summary = create_label()
        layout.addWidget(self.title)
        layout.addWidget(self.summary)
        self.overview = StateOverview()
        layout.addWidget(self.overview)
        # Самые важные действия доступны до длинного разбора решений.
        controls = QHBoxLayout()
        self.compare_button = action_button(
            "Сравнить прохождения", "Узнать, какой выбор изменил результат", primary=True
        )
        self.change_button = action_button("Изменить решение", "Старый результат сохранится")
        self.compare_button.clicked.connect(self.compare_requested.emit)
        self.change_button.clicked.connect(self.decisions_requested.emit)
        controls.addWidget(self.compare_button)
        controls.addWidget(self.change_button)
        layout.addLayout(controls)
        self.retry_button = action_button("Попробовать снова", "Новое прохождение с начала")
        self.retry_button.clicked.connect(self.retry_requested.emit)
        layout.addWidget(self.retry_button)
        layout.addWidget(create_label("Чему учат ваши решения", "heading"))
        self.decisions = QVBoxLayout()
        layout.addLayout(self.decisions)
        self.alternatives = create_label("", "badge")
        layout.addWidget(self.alternatives)
        self.details_button = action_button("Виртуальный компьютер", "Посмотреть итоговый снимок")
        self.details_button.clicked.connect(self.details_requested.emit)
        layout.addWidget(self.details_button)
        self.menu_button = action_button("В главное меню")
        self.menu_button.clicked.connect(self.menu_requested.emit)
        layout.addWidget(self.menu_button)

    def render(self, scenario: Scenario, entries: list[HistoryEntry], active: HistoryEntry) -> None:
        self.title.setText(scenario.node(active.node_id).title)
        self.summary.setText(state_summary(active.state))
        self.overview.render(active.state)
        clear_layout(self.decisions)
        path = history_path(entries, active.id)
        suggestions = []
        for before, after in zip(path, path[1:], strict=False):
            rating = decision_rating(before.state, after.state)
            panel, contents = create_panel(f"{rating} · {after.choice_title}")
            panel.setProperty("rating", "risk" if rating == "Риск вырос" else "helpful")
            contents.addWidget(
                create_label(
                    f"Риск: {before.state.risk} → {after.state.risk}. "
                    + explain_decision(after.choice_id, before.state, after.state)
                )
            )
            self.decisions.addWidget(panel)
            if rating == "Риск вырос":
                other_choices = [
                    choice.title
                    for choice in scenario.node(before.node_id).choices
                    if choice.id != after.choice_id
                ]
                suggestions.append(
                    f"Вместо «{after.choice_title}» попробуйте: " + "; ".join(other_choices) + "."
                )
        self.alternatives.setText(
            "Что можно сделать иначе\n" + "\n\n".join(suggestions)
            if suggestions
            else "Вы сохранили пароль и файлы. Полезная привычка: проверяйте адрес и подтверждайте "
            "просьбы через известный канал. Теперь можно вернуться и сравнить другой выбор."
        )
