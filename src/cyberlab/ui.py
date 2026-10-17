"""Навигация окна: меню → ситуация → последствие → итог. Данные хранит LabSession."""

import sqlite3
from collections.abc import Callable
from datetime import datetime

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from cyberlab.learning import history_path
from cyberlab.review_pages import ComparisonPage, DecisionsPage
from cyberlab.session import LabSession
from cyberlab.simulation_pages import ConsequencePage, ResultsPage, SituationPage
from cyberlab.styles import STYLESHEET
from cyberlab.tutorial import TutorialPage
from cyberlab.ui_helpers import action_button, create_label, make_scrollable
from cyberlab.virtual_computer import VirtualComputer


class MainWindow(QMainWindow):
    def __init__(self, lab: LabSession, settings: QSettings | None = None) -> None:
        super().__init__()
        self.lab = lab
        # Настройки обучения отделены от снимков: схема старой SQLite остаётся v1.
        self.settings = settings if settings is not None else QSettings("CYBERLAB", "CYBERLAB")
        saved_id = self.settings.value("last_session", "", type=str)
        if any(session.id == saved_id for session in lab.repository.sessions(lab.scenario.id)):
            lab.open_session(saved_id)
        self.back_stack: list[QWidget] = []
        self.pages: dict[QWidget, QWidget] = {}
        self.tutorial_starts_session = False
        self.setWindowTitle("CYBERLAB — лаборатория решений")
        # Qt считает размеры в логических пикселях: при масштабе 150% их меньше.
        self.setMinimumSize(600, 400)
        available = self.screen().availableGeometry()
        self.resize(min(1280, available.width() - 40), min(800, available.height() - 40))
        self.setStyleSheet(STYLESHEET)
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 12, 16, 12)
        header = QHBoxLayout()
        header.addWidget(create_label("CYBERLAB", "brand", wrap=False))
        header.addStretch()
        self.back_button = action_button("Назад")
        self.back_button.setMaximumWidth(150)
        self.back_button.clicked.connect(self._back)
        header.addWidget(self.back_button)
        self.menu_button = action_button("В главное меню")
        self.menu_button.setMaximumWidth(220)
        self.menu_button.clicked.connect(self.show_menu)
        header.addWidget(self.menu_button)
        layout.addLayout(header)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        self.menu = self._create_menu()
        self.situation = SituationPage()
        self.consequence = ConsequencePage()
        self.results = ResultsPage()
        self.decisions = DecisionsPage()
        self.comparison = ComparisonPage()
        self.tutorial = TutorialPage()
        self.computer = VirtualComputer()
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
        self.decisions.entry_requested.connect(self._go_to)
        self.decisions.alternative_requested.connect(self._try_alternative)
        self.decisions.root_requested.connect(self._return_to_start)
        self.decisions.compare_requested.connect(self._open_comparison)
        self.tutorial.finished.connect(self._finish_tutorial)
        self.comparison.states_selected.connect(self.computer.render_comparison)
        self.show_menu()

    def _add_page(self, page: QWidget) -> None:
        # Каждому экрану доступна вертикальная прокрутка. Ограничиваем ширину
        # чтения, но не фиксируем высоту русского текста или карточек решений.
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 8, 0, 8)
        row.addStretch()
        page.setMaximumWidth(1080)
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
        self.menu_button.setVisible(page is not self.menu)
        page.setFocus(Qt.FocusReason.OtherFocusReason)

    def _back(self) -> None:
        if self.back_stack:
            self._show(self.back_stack.pop())

    def _create_menu(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addStretch()
        layout.addWidget(create_label("Каждое решение меняет историю", "storyTitle"))
        layout.addWidget(
            create_label(
                "Учитесь распознавать киберугрозы, принимайте решения "
                "и наблюдайте за их последствиями"
            )
        )
        layout.addWidget(
            create_label(
                "Один сценарий · Несколько исходов · Можно вернуться и попробовать иначе", "muted"
            )
        )
        self.start_button = action_button("Начать симуляцию", self.lab.scenario.title, primary=True)
        self.start_button.setObjectName("start_simulation")
        self.start_button.clicked.connect(self._start)
        layout.addWidget(self.start_button)
        self.resume_button = action_button("Продолжить прохождение", "Открыть сохранённый шаг")
        self.resume_button.setObjectName("resume_simulation")
        self.resume_button.clicked.connect(lambda: self._perform(self._display_active))
        layout.addWidget(self.resume_button)
        self.help_button = action_button("Как это работает", "Короткое интерактивное обучение")
        self.help_button.clicked.connect(self._replay_tutorial)
        layout.addWidget(self.help_button)
        self.sessions_button = action_button("История прохождений")
        self.sessions_button.clicked.connect(self._open_sessions)
        layout.addWidget(self.sessions_button)
        layout.addWidget(
            create_label(
                "Безопасная симуляция: письма, пароли и файлы вымышлены. "
                "Ваш настоящий компьютер не затрагивается. Интернет и регистрация не нужны.",
                "badge",
            )
        )
        layout.addStretch()
        return page

    def show_menu(self) -> None:
        self.back_stack.clear()
        # Возврат к корню не стирает прогресс: важен весь набор снимков, не только active.
        was_started = self.settings.value("last_session", "") == self.lab.session.id
        self.resume_button.setVisible(was_started or len(self.lab.entries) > 1)
        self._show(self.menu)

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
        self.settings.sync()

    def _choose(self, choice_id: str) -> None:
        def save_choice() -> None:
            # Сначала транзакция. Если запись не удалась, остаёмся на ситуации.
            self.lab.choose(choice_id)
            self.settings.setValue("pending_feedback", self.lab.active.id)
            self._remember_session()
            self._display_active()

        self._perform(save_choice)

    def _display_active(self) -> None:
        self.back_stack.clear()
        active = self.lab.active
        entries = self.lab.entries
        self.computer.render(active.state)
        if active.parent_id and self.settings.value("pending_feedback", "") == active.id:
            before = self.lab.repository.entry(active.parent_id, self.lab.session.id)
            self.consequence.render(before, active, terminal=self.lab.node.terminal)
            self._show(self.consequence)
        elif self.lab.node.terminal:
            self.results.render(self.lab.scenario, entries, active)
            self._show(self.results)
        else:
            self.situation.render(self.lab.scenario, entries, active)
            self._show(self.situation)

    def _continue_after_decision(self) -> None:
        self.settings.remove("pending_feedback")
        self.settings.sync()
        self._perform(self._display_active)

    def _open_computer(self) -> None:
        self.computer.render(self.lab.active.state)
        self._show(self.computer, remember=True)

    def _open_decisions(self) -> None:
        self.decisions.render(self.lab.scenario, self.lab.entries, self.lab.active)
        self._show(self.decisions, remember=True)

    def _go_to(self, entry_id: str) -> None:
        def restore() -> None:
            self.lab.go_to(entry_id)
            self.settings.remove("pending_feedback")
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
        layout.addWidget(create_label("История прохождений", "storyTitle"))
        layout.addWidget(
            create_label(
                "Все тренировки сохраняются автоматически. Выберите прохождение, "
                "чтобы продолжить с его последнего выбранного шага."
            )
        )
        self.session_list = QListWidget()
        self.session_list.setWordWrap(True)
        self.session_list.setMinimumHeight(260)
        self.session_list.itemDoubleClicked.connect(lambda _item: self._open_selected_session())
        layout.addWidget(self.session_list)
        self.empty_history = create_label("Пока нет решений. Начните первую симуляцию.", "badge")
        layout.addWidget(self.empty_history)
        self.open_session_button = action_button("Открыть прохождение", primary=True)
        self.open_session_button.clicked.connect(self._open_selected_session)
        layout.addWidget(self.open_session_button)
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
                    f"{status}: {self.lab.scenario.node(active.node_id).title}"
                    f"\nРешений в текущем пути: {decisions} · Сохранённых шагов: {len(entries)}"
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
