"""Текущая ситуация, короткое последствие и разбор результата без служебных панелей."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QProgressBar, QVBoxLayout, QWidget

from cyberlab.domain import ComputerState, Scenario
from cyberlab.learning import (
    decision_rating,
    history_path,
    remaining_decisions,
    risk_level,
)
from cyberlab.mentor import explain_decision, explain_state, explain_step
from cyberlab.storage import HistoryEntry
from cyberlab.ui_helpers import (
    action_button,
    choice_button,
    clear_layout,
    create_label,
    create_panel,
    link_button,
)


class StateOverview(QWidget):
    """Число и состояние — в строке. Объяснение условной шкалы доступно при наведении."""

    def __init__(self, *, compact: bool = False) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)
        self.risk = create_label("", "heading")
        self.risk.setToolTip(
            "Учебный риск — условная шкала 0–100, а не вероятность атаки. "
            "Чем выше значение, тем опаснее ситуация в сценарии."
        )
        self.meter = QProgressBar()
        self.meter.setRange(0, 100)
        self.meter.setTextVisible(False)
        self.meter.setFixedHeight(3)
        self.meter.setMaximumWidth(220)
        self.status = create_label("", "muted")
        layout.addWidget(self.risk)
        layout.addWidget(self.meter)
        layout.addWidget(self.status)
        self.status.setVisible(not compact)

    def render(self, state: ComputerState) -> None:
        self.risk.setText(f"Риск: {state.risk} / 100 · {risk_level(state.risk)}")
        self.meter.setValue(state.risk)
        password = "раскрыт" if state.credentials_exposed else "защищён"
        files = "недоступны" if state.files_encrypted else "доступны"
        network = "подключена" if state.network_connected else "отключена"
        self.status.setText(f"Учебный пароль: {password} · Файлы: {files} · Сеть: {network}")
        details = []
        if state.attachment_opened:
            details.append("Вложение открыто")
        if state.macros_enabled:
            details.append("Макросы разрешены")
        if state.usb_connected:
            details.append("USB подключён")
        if state.malware_active:
            details.append("Программа активна")
        if details:
            self.status.setText(self.status.text() + "\n" + " · ".join(details))


class SituationPage(QWidget):
    choice_selected = Signal(str)
    details_requested = Signal()
    decisions_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        self.progress_text = create_label("", "eyebrow")
        layout.addWidget(self.progress_text)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(2)
        layout.addWidget(self.progress)
        self.title = create_label("", "storyTitle")
        self.description = create_label()
        layout.addWidget(self.title)
        layout.addWidget(self.description)
        layout.addSpacing(8)
        layout.addWidget(create_label("ВАШЕ ДЕЙСТВИЕ", "eyebrow"))
        self.actions = QVBoxLayout()
        self.actions.setSpacing(0)
        layout.addLayout(self.actions)
        layout.addSpacing(8)
        self.overview = StateOverview()
        layout.addWidget(self.overview)
        self.mentor_toggle = link_button("Подсказка наставника")
        self.mentor_toggle.setCheckable(True)
        self.mentor = create_label("", "muted")
        self.mentor.hide()
        self.mentor_toggle.toggled.connect(self.mentor.setVisible)
        layout.addWidget(self.mentor_toggle, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.mentor)
        layout.addStretch()
        # Общие кнопки компьютера и решений назначает MainWindow: они находятся в навигации.

    def render(self, scenario: Scenario, entries: list[HistoryEntry], active: HistoryEntry) -> None:
        node = scenario.node(active.node_id)
        made = len(history_path(entries, active.id)) - 1
        remaining = remaining_decisions(scenario, node.id)
        self.progress_text.setText(f"СЦЕНАРИЙ / ШАГ {made + 1}")
        self.progress_text.setToolTip(
            f"{scenario.title}. Принято решений: {made}. До итога: не более {remaining}."
        )
        self.progress.setRange(0, max(1, made + remaining))
        self.progress.setValue(made)
        self.title.setText(node.title)
        self.description.setText(node.description)
        clear_layout(self.actions)
        for number, choice in enumerate(node.choices, 1):
            button = choice_button(number, choice.title, choice.hint)
            button.setObjectName(f"choice_{choice.id}")
            button.clicked.connect(
                lambda _checked=False, choice_id=choice.id: self.choice_selected.emit(choice_id)
            )
            self.actions.addWidget(button)
        self.overview.render(active.state)
        self.mentor_toggle.setChecked(False)
        self.mentor.setText(explain_state(active.state, scenario))


class ConsequencePage(QWidget):
    continue_requested = Signal()
    details_requested = Signal()
    alternative_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        layout.addWidget(create_label("ПОСЛЕДСТВИЕ", "eyebrow"))
        self.action = create_label("", "storyTitle")
        layout.addWidget(self.action)
        self.event = create_label()
        layout.addWidget(self.event)
        self.reason = create_label("", "muted")
        layout.addWidget(self.reason)
        layout.addSpacing(14)
        self.risk_change = create_label("", "heading")
        layout.addWidget(self.risk_change)
        self.overview = StateOverview()
        self.overview.risk.hide()  # Значения до/после уже показаны строкой выше.
        layout.addWidget(self.overview)
        self.next_step = create_label("", "caption")
        layout.addWidget(self.next_step)
        layout.addSpacing(8)
        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.continue_button = action_button("Продолжить", primary=True)
        self.continue_button.setObjectName("continue_after_decision")
        self.continue_button.clicked.connect(self.continue_requested.emit)
        self.alternative_button = link_button("Изменить выбор")
        self.alternative_button.clicked.connect(self.alternative_requested.emit)
        controls.addWidget(self.continue_button)
        controls.addWidget(self.alternative_button)
        controls.addStretch()
        layout.addLayout(controls)
        layout.addStretch()

    def render(
        self,
        before: HistoryEntry,
        after: HistoryEntry,
        *,
        terminal: bool,
        scenario: Scenario | None = None,
    ) -> None:
        self.action.setText(after.choice_title)
        self.event.setText(after.state.events[-1])
        self.reason.setText(
            explain_step(scenario, before, after)
            if scenario is not None
            else explain_decision(after.choice_id, before.state, after.state)
        )
        difference = after.state.risk - before.state.risk
        change = f"{difference:+d}" if difference else "без изменения"
        self.risk_change.setText(f"Риск: {before.state.risk} → {after.state.risk} / 100 ({change})")
        self.overview.render(after.state)
        self.next_step.setText("Ветка завершена. Далее — разбор решений." if terminal else "")
        self.next_step.setVisible(terminal)


class ResultsPage(QWidget):
    retry_requested = Signal()
    decisions_requested = Signal()
    compare_requested = Signal()
    menu_requested = Signal()
    details_requested = Signal()
    export_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(create_label("ПРОХОЖДЕНИЕ ЗАВЕРШЕНО", "eyebrow"))
        self.title = create_label("", "storyTitle")
        layout.addWidget(self.title)
        self.overview = StateOverview()
        layout.addWidget(self.overview)
        self.risk_history = create_label("", "muted")
        layout.addWidget(self.risk_history)
        self.export_button = link_button("Сохранить отчёт TXT")
        self.export_button.clicked.connect(self.export_requested.emit)
        layout.addWidget(self.export_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.export_status = create_label("", "caption")
        layout.addWidget(self.export_status)
        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.compare_button = action_button("Сравнить результаты", primary=True)
        self.change_button = action_button("Изменить решение")
        self.retry_button = link_button("Заново", "Создать новое прохождение")
        self.compare_button.clicked.connect(self.compare_requested.emit)
        self.change_button.clicked.connect(self.decisions_requested.emit)
        self.retry_button.clicked.connect(self.retry_requested.emit)
        controls.addWidget(self.compare_button)
        controls.addWidget(self.change_button)
        controls.addWidget(self.retry_button)
        controls.addStretch()
        layout.addLayout(controls)
        layout.addSpacing(12)
        self.details_toggle = link_button("Разбор решений и альтернативы")
        self.details_toggle.setCheckable(True)
        layout.addWidget(self.details_toggle, alignment=Qt.AlignmentFlag.AlignLeft)
        self.details_body = QWidget()
        self.decisions = QVBoxLayout(self.details_body)
        self.decisions.setContentsMargins(0, 0, 0, 0)
        self.decisions.setSpacing(0)
        layout.addWidget(self.details_body)
        self.alternatives = create_label("", "muted")
        self.details_toggle.toggled.connect(self.details_body.setVisible)
        self.details_toggle.toggled.connect(self.alternatives.setVisible)
        layout.addWidget(self.alternatives)
        self.details_body.hide()
        self.alternatives.hide()
        layout.addStretch()

    def render(self, scenario: Scenario, entries: list[HistoryEntry], active: HistoryEntry) -> None:
        self.title.setText(scenario.node(active.node_id).title)
        self.overview.render(active.state)
        clear_layout(self.decisions)
        path = history_path(entries, active.id)
        self.details_toggle.setChecked(False)
        self.export_status.clear()
        self.risk_history.setText(
            "Динамика риска: "
            + " → ".join(str(entry.state.risk) for entry in path)
            + f" · Решений: {len(path) - 1}"
        )
        suggestions = []
        for before, after in zip(path, path[1:], strict=False):
            rating = decision_rating(before.state, after.state)
            panel, contents = create_panel(after.choice_title)
            panel.setObjectName("resultRow")
            contents.addWidget(
                create_label(f"{rating} · Риск {before.state.risk} → {after.state.risk}", "caption")
            )
            contents.addWidget(create_label(explain_step(scenario, before, after), "muted"))
            self.decisions.addWidget(panel)
            if rating == "Риск вырос":
                alternatives = [
                    choice.title
                    for choice in scenario.node(before.node_id).choices
                    if choice.id != after.choice_id
                ]
                suggestions.append(
                    f"Вместо «{after.choice_title}»: " + "; ".join(alternatives) + "."
                )
        self.alternatives.setText(
            "Можно было иначе\n" + "\n".join(suggestions)
            if suggestions
            else "Пароль и файлы защищены. Можно вернуться к выбору и сравнить другой результат."
        )
