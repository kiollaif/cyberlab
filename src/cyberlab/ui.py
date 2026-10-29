"""Навигация окна: меню → ситуация → последствие → итог. Данные хранит LabSession."""

import sqlite3
from collections.abc import Callable
from datetime import datetime

from PySide6.QtCore import QIODevice, QSaveFile, QSettings, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from cyberlab.ai_context import build_context
from cyberlab.ai_panel import AiMentorPanel
from cyberlab.learning import history_path
from cyberlab.navigation import WorkspaceNavigation
from cyberlab.reports import build_report
from cyberlab.review_pages import ComparisonPage, DecisionsPage
from cyberlab.scenarios import SCENARIOS, get_scenario
from cyberlab.session import LabSession
from cyberlab.simulation_pages import ConsequencePage, ResultsPage, SituationPage
from cyberlab.styles import STYLESHEET
from cyberlab.tutorial import TutorialPage
from cyberlab.ui_helpers import action_button, create_label, link_button, make_scrollable
from cyberlab.virtual_computer import VirtualComputer


class MainWindow(QMainWindow):
    def __init__(self, lab: LabSession, settings: QSettings | None = None) -> None:
        super().__init__()
        self.lab = lab
        # Настройки обучения отделены от снимков: схема старой SQLite остаётся v1.
        self.settings = settings if settings is not None else QSettings("CYBERLAB", "CYBERLAB")
        scenario_id = self.settings.value("last_scenario", lab.scenario.id, type=str)
        if scenario_id != lab.scenario.id:
            try:
                lab.switch_scenario(get_scenario(scenario_id))
            except ValueError:
                pass  # Удалённый/неизвестный сценарий не мешает открыть доступную тренировку.
        saved_id = self.settings.value("last_session", "", type=str)
        if any(session.id == saved_id for session in lab.repository.sessions(lab.scenario.id)):
            lab.open_session(saved_id)
        self.back_stack: list[QWidget] = []
        self.pages: dict[QWidget, QWidget] = {}
        self.tutorial_starts_session = False
        self._close_when_ai_finishes = False
        self.setWindowTitle("CYBERLAB — лаборатория решений")
        # Qt считает размеры в логических пикселях: при масштабе 150% их меньше.
        self.setMinimumSize(600, 400)
        available = self.screen().availableGeometry()
        self.resize(min(1366, available.width() - 40), min(850, available.height() - 40))
        self.setStyleSheet(STYLESHEET)
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.navigation = WorkspaceNavigation()
        self.navigation.navigate.connect(self._navigate)
        layout.addWidget(self.navigation)
        workspace = QWidget()
        workspace.setObjectName("workspace")
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)
        topbar = QWidget()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(52)
        header = QHBoxLayout(topbar)
        header.setContentsMargins(28, 0, 28, 0)
        header.setSpacing(12)
        self.back_button = link_button("Назад")
        self.back_button.clicked.connect(self._back)
        header.addWidget(self.back_button)
        self.breadcrumb = create_label("", "breadcrumb")
        header.addWidget(self.breadcrumb, 1)
        workspace_layout.addWidget(topbar)
        self.menu_button = self.navigation.buttons["home"]
        self.stack = QStackedWidget()
        workspace_layout.addWidget(self.stack, 1)
        layout.addWidget(workspace, 1)

        self.menu = self._create_menu()
        self.situation = SituationPage()
        self.consequence = ConsequencePage()
        self.results = ResultsPage()
        self.decisions = DecisionsPage()
        self.comparison = ComparisonPage()
        self.tutorial = TutorialPage()
        self.computer = VirtualComputer()
        self.ai_mentor = AiMentorPanel()
        self.ai_mentor.idle.connect(self._finish_pending_close)
        self.computer.setMinimumHeight(450)
        self.saved_sessions = self._create_sessions_page()
        for page in (
            self.menu,
            self.situation,
            self.consequence,
            self.results,
            self.decisions,
            self.comparison,
            self.tutorial,
            self.computer,
            self.saved_sessions,
            self.ai_mentor,
        ):
            self._add_page(page)
        self.situation.choice_selected.connect(self._choose)
        self.situation.details_requested.connect(self._open_computer)
        self.situation.decisions_requested.connect(self._open_decisions)
        self.consequence.continue_requested.connect(self._continue_after_decision)
        self.consequence.details_requested.connect(self._open_computer)
        self.consequence.alternative_requested.connect(self._try_alternative)
        self.results.retry_requested.connect(lambda: self._perform(self._start_new_session))
        self.results.decisions_requested.connect(self._open_decisions)
        self.results.compare_requested.connect(self._open_comparison)
        self.results.menu_requested.connect(self.show_menu)
        self.results.details_requested.connect(self._open_computer)
        self.results.export_requested.connect(self._export_report)
        self.decisions.entry_requested.connect(self._go_to)
        self.decisions.alternative_requested.connect(self._try_alternative)
        self.decisions.root_requested.connect(self._return_to_start)
        self.decisions.compare_requested.connect(self._open_comparison)
        self.tutorial.finished.connect(self._finish_tutorial)
        self.comparison.states_selected.connect(self.computer.render_comparison)
        self.comparison.states_selected.connect(self._comparison_context_changed)
        # Общие действия больше не повторяются крупными кнопками на каждом экране.
        # Ссылки нужны обработчикам и тестам; сам виджет существует в одном экземпляре.
        self.ai_buttons = dict.fromkeys(
            (self.menu, self.situation, self.consequence, self.results, self.comparison),
            self.navigation.buttons["mentor"],
        )
        for page in (self.situation, self.consequence, self.results):
            page.details_button = self.navigation.buttons["computer"]
        self.situation.decisions_button = self.navigation.buttons["decisions"]
        self.decisions.compare_button = self.navigation.buttons["comparison"]
        self.results.menu_button = self.menu_button
        self.help_button = self.navigation.buttons["help"]
        self.sessions_button = self.navigation.buttons["sessions"]
        self.show_menu()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "navigation"):
            self.navigation.set_compact(self.width() < 980)

    def _navigate(self, section: str) -> None:
        if section == getattr(self, "_current_section", None):
            self.navigation.select(section)
            return
        actions = {
            "home": self.show_menu,
            "simulation": self._resume,
            "decisions": self._open_decisions,
            "comparison": self._open_comparison,
            "sessions": self._open_sessions,
            "computer": self._open_computer,
            "mentor": self._open_ai,
            "help": self._replay_tutorial,
        }
        self._perform(actions[section])

    def _resume(self) -> None:
        self._remember_session()
        self._display_active()

    def _add_page(self, page: QWidget) -> None:
        # Каждому экрану доступна вертикальная прокрутка. Ограничиваем ширину
        # чтения, но не фиксируем высоту русского текста или карточек решений.
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(28, 30, 28, 24)
        row.addStretch()
        page.setMaximumWidth(960)
        page.layout().setContentsMargins(0, 0, 0, 0)
        row.addWidget(page, 1)
        row.addStretch()
        scroll = make_scrollable(container)
        self.pages[page] = scroll
        self.stack.addWidget(scroll)

    def _show(self, page: QWidget, *, remember: bool = False) -> None:
        if remember:
            self.back_stack.append(self.current_page)
        self.current_page = page
        self.stack.setCurrentWidget(self.pages[page])
        self.pages[page].verticalScrollBar().setValue(0)
        self.back_button.setVisible(bool(self.back_stack))
        sections = {
            self.menu: "home",
            self.situation: "simulation",
            self.consequence: "simulation",
            self.results: "simulation",
            self.decisions: "decisions",
            self.comparison: "comparison",
            self.saved_sessions: "sessions",
            self.computer: "computer",
            self.ai_mentor: "mentor",
            self.tutorial: "help",
        }
        section = sections[page]
        self._current_section = section
        self.navigation.select(section)
        self.breadcrumb.setText(f"Рабочее пространство  /  {self.navigation.titles[section]}")
        page.setFocus(Qt.FocusReason.OtherFocusReason)

    def _back(self) -> None:
        if self.back_stack:
            self._show(self.back_stack.pop())

    def _create_menu(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(18)
        layout.addWidget(create_label("Практика кибербезопасности", "storyTitle"))
        layout.addWidget(
            create_label("Распознавайте угрозы и проверяйте последствия своих решений.", "muted")
        )
        layout.addSpacing(24)
        layout.addWidget(create_label("СЦЕНАРИИ", "eyebrow"))
        scenario_row = QFrame()
        scenario_row.setObjectName("scenarioRow")
        scenario_layout = QVBoxLayout(scenario_row)
        scenario_layout.setContentsMargins(0, 22, 0, 22)
        scenario_layout.setSpacing(12)
        self.scenario_selector = QComboBox()
        self.scenario_selector.setAccessibleName("Учебный сценарий")
        for scenario in SCENARIOS:
            self.scenario_selector.addItem(scenario.title, scenario.id)
        self.scenario_selector.setCurrentIndex(
            self.scenario_selector.findData(self.lab.scenario.id)
        )
        self.scenario_selector.currentIndexChanged.connect(self._select_scenario)
        scenario_layout.addWidget(self.scenario_selector)
        self.scenario_description = create_label(self.lab.scenario.summary, "muted")
        scenario_layout.addWidget(self.scenario_description)
        self.start_button = action_button("Начать симуляцию", primary=True)
        self.start_button.setObjectName("start_simulation")
        self.start_button.clicked.connect(self._start)
        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addWidget(self.start_button)
        self.resume_button = action_button("Продолжить прохождение")
        self.resume_button.setObjectName("resume_simulation")
        self.resume_button.clicked.connect(lambda: self._perform(self._display_active))
        actions.addWidget(self.resume_button)
        actions.addStretch()
        scenario_layout.addLayout(actions)
        layout.addWidget(scenario_row)
        layout.addStretch()
        layout.addWidget(
            create_label(
                "Изолированная учебная среда. Настоящие файлы в безопасности.",
                "caption",
            )
        )
        return page

    def show_menu(self) -> None:
        self.back_stack.clear()
        # Возврат к корню не стирает прогресс: важен весь набор снимков, не только active.
        was_started = self.settings.value("last_session", "") == self.lab.session.id
        self.resume_button.setVisible(was_started or len(self.lab.entries) > 1)
        self._show(self.menu)

    def _select_scenario(self, index: int) -> None:
        def select() -> None:
            self.lab.switch_scenario(get_scenario(self.scenario_selector.itemData(index)))
            self.scenario_description.setText(self.lab.scenario.summary)
            self.settings.setValue("last_scenario", self.lab.scenario.id)
            self.settings.sync()
            self.ai_mentor.set_context(
                build_context(self.lab.scenario, self.lab.entries, self.lab.active)
            )
            self.show_menu()

        self._perform(select)
        self.scenario_selector.blockSignals(True)
        self.scenario_selector.setCurrentIndex(
            self.scenario_selector.findData(self.lab.scenario.id)
        )
        self.scenario_selector.blockSignals(False)

    def _export_report(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить учебный отчёт",
            f"CYBERLAB-{self.lab.scenario.id}.txt",
            "Текст UTF-8 (*.txt)",
        )
        if not filename:
            return

        def save() -> None:
            self.results.export_status.clear()
            data = build_report(self.lab.scenario, self.lab.entries, self.lab.active).encode(
                "utf-8"
            )
            # QSaveFile сначала пишет временный файл: ошибка не повреждает прежний отчёт.
            target = QSaveFile(filename)
            if not target.open(QIODevice.OpenModeFlag.WriteOnly):
                raise OSError(target.errorString())
            if target.write(data) != len(data) or not target.commit():
                target.cancelWriting()
                raise OSError(target.errorString())
            self.results.export_status.setText("Отчёт сохранён.")

        self._perform(save)

    def _perform(self, action: Callable[[], object]) -> None:
        try:
            action()
        except (sqlite3.Error, ValueError, OSError) as error:
            QMessageBox.critical(self, "Не удалось открыть или сохранить прохождение", str(error))

    def _start(self) -> None:
        if not self.settings.value("tutorial_completed", False, type=bool):
            self.tutorial_starts_session = True
            self.tutorial.reset()
            self._show(self.tutorial, remember=True)
        else:
            self._perform(self._start_new_session)

    def _replay_tutorial(self) -> None:
        self.tutorial_starts_session = False
        self.tutorial.reset()
        self._show(self.tutorial, remember=True)

    def _finish_tutorial(self) -> None:
        self.settings.setValue("tutorial_completed", True)
        self.settings.sync()
        if self.tutorial_starts_session:
            self._perform(self._start_new_session)
        else:
            self.show_menu()

    def _start_new_session(self) -> None:
        # LabSession уже создаёт пустую тренировку при первом запуске.
        # Используем её, чтобы не заполнять историю лишними пустыми сессиями.
        if len(self.lab.entries) > 1:
            self.lab.new_session()
        self.settings.remove("pending_feedback")
        self._remember_session()
        self._display_active()

    def _remember_session(self) -> None:
        self.settings.setValue("last_session", self.lab.session.id)
        self.settings.setValue("last_scenario", self.lab.scenario.id)
        self.settings.sync()

    def _choose(self, choice_id: str) -> None:
        def save_choice() -> None:
            # Сначала транзакция. Если запись не удалась, остаёмся на ситуации.
            self.lab.choose(choice_id)
            self.settings.setValue("pending_feedback", self.lab.active.id)
            self.settings.setValue(f"feedback/{self.lab.session.id}", self.lab.active.id)
            self._remember_session()
            self._display_active()

        self._perform(save_choice)

    def _display_active(self) -> None:
        self.back_stack.clear()
        active = self.lab.active
        entries = self.lab.entries
        self.ai_mentor.set_context(build_context(self.lab.scenario, entries, active))
        self.computer.set_scenario(self.lab.scenario)
        self.computer.render(active.state)
        pending = self.settings.value(
            f"feedback/{self.lab.session.id}", self.settings.value("pending_feedback", "")
        )
        if active.parent_id and pending == active.id:
            before = self.lab.repository.entry(active.parent_id, self.lab.session.id)
            self.consequence.render(
                before, active, terminal=self.lab.node.terminal, scenario=self.lab.scenario
            )
            self._show(self.consequence)
        elif self.lab.node.terminal:
            self.results.render(self.lab.scenario, entries, active)
            self._show(self.results)
        else:
            self.situation.render(self.lab.scenario, entries, active)
            self._show(self.situation)

    def _continue_after_decision(self) -> None:
        self.settings.remove("pending_feedback")
        self.settings.remove(f"feedback/{self.lab.session.id}")
        self.settings.sync()
        self._perform(self._display_active)

    def _open_computer(self) -> None:
        self.computer.set_scenario(self.lab.scenario)
        self.computer.render(self.lab.active.state)
        self._show(self.computer, remember=True)

    def _open_ai(self) -> None:
        if self.current_page is self.comparison:
            self._comparison_context_changed()
        else:
            self.ai_mentor.set_context(
                build_context(self.lab.scenario, self.lab.entries, self.lab.active)
            )
        self._show(self.ai_mentor, remember=True)

    def _comparison_context_changed(self, *_states) -> None:
        selected = [combo.currentData() for combo in self.comparison.selectors]
        if any(entry_id is None for entry_id in selected):
            return
        pair = tuple(self.comparison.entries_by_id[entry_id] for entry_id in selected)
        self.ai_mentor.set_context(
            build_context(
                self.lab.scenario, self.comparison.entries, self.lab.active, comparison=pair
            )
        )

    def closeEvent(self, event) -> None:
        if self.ai_mentor.busy:
            # Не уничтожаем работающий QThread. Закрытие завершится асинхронно
            # после ответа или тайм-аута; цикл Qt и сценарий не блокируются.
            self._close_when_ai_finishes = True
            self.ai_mentor.cancel_display()
            event.ignore()
            return
        super().closeEvent(event)

    def _finish_pending_close(self) -> None:
        if self._close_when_ai_finishes:
            self.close()

    def _open_decisions(self) -> None:
        self.decisions.render(self.lab.scenario, self.lab.entries, self.lab.active)
        self._show(self.decisions, remember=True)

    def _go_to(self, entry_id: str) -> None:
        def restore() -> None:
            self.lab.go_to(entry_id)
            self.settings.remove("pending_feedback")
            self.settings.remove(f"feedback/{self.lab.session.id}")
            self._remember_session()
            self._display_active()

        self._perform(restore)

    def _try_alternative(self) -> None:
        if self.lab.active.parent_id is not None:
            self._go_to(self.lab.active.parent_id)

    def _return_to_start(self) -> None:
        self._go_to(self.lab.entries[0].id)

    def _open_comparison(self) -> None:
        def show_comparison() -> None:
            self.computer.set_scenario(self.lab.scenario)
            sessions = list(reversed(self.lab.repository.sessions(self.lab.scenario.id)))
            numbers = {session.id: index for index, session in enumerate(sessions, 1)}
            entries = []
            for session in sessions:
                entries.extend(self.lab.repository.entries(session.id))
            self.comparison.render(self.lab.scenario, entries, numbers, self.lab.active)
            self._show(self.comparison, remember=True)

        self._perform(show_comparison)

    def _create_sessions_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)
        layout.addWidget(create_label("Прохождения", "storyTitle"))
        layout.addWidget(create_label("Сохранённые тренировки и результаты.", "muted"))
        self.session_list = QListWidget()
        self.session_list.setWordWrap(True)
        self.session_list.setMinimumHeight(260)
        self.session_list.itemDoubleClicked.connect(lambda _item: self._open_selected_session())
        layout.addWidget(self.session_list)
        self.empty_history = create_label("Пока нет решений. Начните первую симуляцию.", "badge")
        layout.addWidget(self.empty_history)
        self.open_session_button = action_button("Открыть прохождение", primary=True)
        self.open_session_button.clicked.connect(self._open_selected_session)
        layout.addWidget(self.open_session_button, alignment=Qt.AlignmentFlag.AlignLeft)
        return page

    def _open_sessions(self) -> None:
        def show_sessions() -> None:
            self.session_list.clear()
            sessions = list(reversed(self.lab.repository.sessions(self.lab.scenario.id)))
            for number, session in reversed(list(enumerate(sessions, 1))):
                entries = self.lab.repository.entries(session.id)
                if len(entries) == 1:
                    continue
                active = self.lab.repository.entry(session.active_entry_id, session.id)
                date = (
                    datetime.fromisoformat(entries[0].created_at)
                    .astimezone()
                    .strftime("%d.%m.%Y %H:%M")
                )
                status = "Итог" if self.lab.scenario.node(active.node_id).terminal else "В процессе"
                decisions = len(history_path(entries, active.id)) - 1
                item = QListWidgetItem(
                    f"Прохождение {number} · {date}\n"
                    f"{status}: {self.lab.scenario.node(active.node_id).title} "
                    f"· Риск {active.state.risk}/100"
                )
                item.setToolTip(
                    f"Решений в пути: {decisions}. Всего сохранено шагов: {len(entries)}."
                )
                item.setData(Qt.ItemDataRole.UserRole, session.id)
                self.session_list.addItem(item)
            self.empty_history.setVisible(self.session_list.count() == 0)
            self.open_session_button.setEnabled(self.session_list.count() > 0)
            self.session_list.setCurrentRow(0)
            self._show(self.saved_sessions, remember=True)

        self._perform(show_sessions)

    def _open_selected_session(self) -> None:
        item = self.session_list.currentItem()
        if item is None:
            return

        def open_saved() -> None:
            self.lab.open_session(item.data(Qt.ItemDataRole.UserRole))
            self._remember_session()
            self._display_active()

        self._perform(open_saved)
