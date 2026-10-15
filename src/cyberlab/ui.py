"""Главное окно: дерево решений, текущая ситуация, виртуальный ПК и сравнение."""

import sqlite3
from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from cyberlab.domain import VIRTUAL_FILES, ComputerState, compare_states
from cyberlab.session import LabSession
from cyberlab.storage import HistoryEntry

STYLESHEET = """
QWidget { background: #101922; color: #e1eaf0; font-size: 13px; }
QMainWindow, QWidget#root { background: #0b1119; }
QFrame#panel { border: 1px solid #293746; border-radius: 10px; }
QFrame#metric { background: #15212d; border: 1px solid #293746; border-radius: 8px; }
QLabel { background: transparent; }
QLabel#brand { color: #60e2bd; font-size: 26px; font-weight: 800; letter-spacing: 3px; }
QLabel#heading { font-size: 17px; font-weight: 700; }
QLabel#storyTitle { font-size: 23px; font-weight: 700; }
QLabel#muted { color: #9aafbe; }
QLabel#badge { color: #60e2bd; background: #16372f; border-radius: 6px; padding: 8px; }
QLabel#metricValue { color: #60e2bd; font-size: 20px; font-weight: 700; }
QPushButton { background: #203141; border: 1px solid #3a5163; border-radius: 7px;
              padding: 9px 13px; text-align: left; }
QPushButton:hover { background: #29475a; border-color: #60e2bd; }
QPushButton:focus { border: 2px solid #60e2bd; }
QPushButton[role="choice"] { background: #18382f; border-color: #2b6e58; }
QPushButton:disabled { color: #71818c; }
QTreeWidget, QListWidget, QTextEdit { background: #101922; border: 1px solid #293746;
                                  border-radius: 6px; padding: 5px; }
QTreeWidget::item, QListWidget::item { padding: 7px 3px; }
QTreeWidget::item:selected, QListWidget::item:selected { background: #25483f; color: #c8ffec; }
QTabWidget::pane { border: 1px solid #293746; border-radius: 6px; }
QTabBar::tab { background: #15212d; padding: 8px; border-bottom: 2px solid #293746; }
QTabBar::tab:selected { color: #60e2bd; border-bottom-color: #60e2bd; }
QComboBox { background: #1b2a36; padding: 7px; border: 1px solid #3a5163; border-radius: 5px; }
QComboBox QAbstractItemView { background: #1b2a36; selection-background-color: #25483f; }
QTableWidget { background: #101922; border: none; gridline-color: #293746; }
QHeaderView::section { background: #1b2a36; color: #9aafbe; padding: 6px; border: none; }
QSplitter::handle { background: #0b1119; width: 8px; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: #101922; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #3a5163; min-height: 24px; border-radius: 4px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip { background: #203141; color: #e1eaf0; border: 1px solid #60e2bd; }
"""


def label(text: str = "", name: str = "", *, wrap: bool = True) -> QLabel:
    widget = QLabel(text)
    widget.setObjectName(name)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(wrap)
    return widget


def panel(title: str) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("panel")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(12)
    layout.addWidget(label(title, "heading"))
    return frame, layout


def scrollable(widget: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(widget)
    return area


class VirtualComputer(QWidget):
    """Экран учебного ПК. Ни один виджет не открывает внешние адреса или файлы."""

    def __init__(self) -> None:
        super().__init__()
        self.state = ComputerState()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label("LAB-01  /  Виртуальный компьютер", "heading"))
        layout.addWidget(label("Почта, файлы и сеть существуют только внутри модели.", "muted"))
        self.tabs = QTabWidget()
        self.tabs.setObjectName("computer_tabs")
        layout.addWidget(self.tabs)

        mail = QWidget()
        mail_layout = QVBoxLayout(mail)
        self.mail_status = label()
        self.mail_status.setObjectName("mail_status")
        mail_layout.addWidget(self.mail_status)
        mail_layout.addWidget(label("IT-поддержка\nКому: сотрудник@cyberlab.example", "heading"))
        mail_layout.addWidget(label("Тема: срочно подтвердите пароль"))
        mail_layout.addWidget(
            label(
                "Ваш пароль истекает через 15 минут. Подтвердите учётную запись, "
                "чтобы сохранить доступ к проекту."
            )
        )
        mail_layout.addWidget(label("[ Подтвердить учётную запись ]", "badge"))
        self.mail_details = label()
        self.mail_details.setObjectName("mail_details")
        mail_layout.addWidget(self.mail_details)
        mail_layout.addStretch()
        self.tabs.addTab(scrollable(mail), "Почта")

        files = QWidget()
        files_layout = QVBoxLayout(files)
        self.file_list = QListWidget()
        self.file_list.setObjectName("virtual_files")
        self.file_list.addItems([file.name for file in VIRTUAL_FILES])
        self.file_list.setMaximumHeight(115)
        self.file_content = QTextEdit()
        self.file_content.setObjectName("file_content")
        self.file_content.setReadOnly(True)
        self.file_content.setAcceptRichText(False)
        files_layout.addWidget(self.file_list)
        files_layout.addWidget(self.file_content)
        self.file_list.currentRowChanged.connect(self._show_file)
        self.file_list.setCurrentRow(0)
        self.tabs.addTab(files, "Файлы")

        self.journal = QListWidget()
        self.journal.setObjectName("event_journal")
        self.journal.setWordWrap(True)
        self.tabs.addTab(self.journal, "Журнал")

        browser = QWidget()
        browser_layout = QVBoxLayout(browser)
        self.browser_status = label()
        self.browser_status.setObjectName("browser_status")
        browser_layout.addWidget(self.browser_status)
        browser_layout.addWidget(label("login.cyberlab-check.invalid", "badge"))
        browser_layout.addWidget(label("Подтвердите учётную запись", "heading"))
        browser_layout.addWidget(
            label(
                "Это макет поддельной страницы. Настоящая сеть не используется. "
                "Отправка вымышленного пароля моделируется выбором решения в центре окна."
            )
        )
        browser_layout.addStretch()
        self.tabs.addTab(scrollable(browser), "Браузер")

    def render(self, state: ComputerState) -> None:
        previous = self.state
        self.state = state
        self.mail_status.setText(
            "КАРАНТИН · письмо изолировано" if state.email_quarantined else "ВХОДЯЩИЕ · 1 письмо"
        )
        self.mail_details.setText(
            "От: help@cyberlab-support.invalid\n"
            "Ссылка: https://login.cyberlab-check.invalid\n"
            "Ожидаемый домен: cyberlab.example"
            if state.email_inspected
            else "Адрес отправителя скрыт за отображаемым именем. Выберите «Проверить письмо»."
        )
        self.journal.clear()
        self.journal.addItems(list(state.events))
        self.browser_status.setText(
            "Страница открыта" if state.browser_open else "Страница закрыта"
        )
        self._show_file(self.file_list.currentRow())
        if state.files_encrypted and not previous.files_encrypted:
            self.tabs.setCurrentIndex(1)
        elif state.browser_open and not previous.browser_open:
            self.tabs.setCurrentIndex(3)
        elif not state.browser_open and previous.browser_open:
            self.tabs.setCurrentIndex(0)

    def _show_file(self, row: int) -> None:
        if row < 0:
            return
        file = VIRTUAL_FILES[row]
        self.file_content.setPlainText(
            f"{file.name}\n\n[Содержимое недоступно]\n"
            "Файл зашифрован в учебной модели. Вернитесь к предыдущему решению, "
            "чтобы восстановить снимок."
            if self.state.files_encrypted
            else file.content
        )


class MainWindow(QMainWindow):
    def __init__(self, lab: LabSession) -> None:
        super().__init__()
        self.lab = lab
        self.entries_by_id: dict[str, HistoryEntry] = {}
        self.setWindowTitle("CYBERLAB — лаборатория решений")
        self.setMinimumSize(1120, 720)
        available = self.screen().availableGeometry()
        self.resize(min(1440, available.width() - 40), min(940, available.height() - 40))
        self.setStyleSheet(STYLESHEET)
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(20, 16, 20, 14)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.addWidget(label("CYBERLAB", "brand", wrap=False))
        header.addWidget(label("Лаборатория решений\nИзучайте угрозы через последствия", "muted"))
        header.addStretch()
        header.addWidget(label("Локальная симуляция", "badge", wrap=False))
        self.restart_button = QPushButton("К началу")
        self.restart_button.setObjectName("return_to_start")
        self.restart_button.setToolTip("Вернуться к корню истории, сохранив все ветки")
        self.restart_button.clicked.connect(self._return_to_start)
        header.addWidget(self.restart_button)
        layout.addLayout(header)

        metrics = QGridLayout()
        self.metric_values: list[QLabel] = []
        for index, title in enumerate(
            ("Учебный риск", "Учётные данные", "Виртуальные файлы", "Сеть")
        ):
            frame = QFrame()
            frame.setObjectName("metric")
            box = QVBoxLayout(frame)
            box.addWidget(label(title, "muted"))
            value = label("", "metricValue", wrap=False)
            self.metric_values.append(value)
            box.addWidget(value)
            metrics.addWidget(frame, 0, index)
        layout.addLayout(metrics)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)
        history_panel, history_layout = panel("История решений")
        history_panel.setMinimumWidth(240)
        history_layout.addWidget(
            label("Выберите шаг и примите другое решение. Старые ветки сохранятся.", "muted")
        )
        self.history = QTreeWidget()
        self.history.setObjectName("decision_history")
        self.history.setHeaderHidden(True)
        self.history.setWordWrap(True)
        self.history.setIndentation(15)
        self.history.itemSelectionChanged.connect(self._history_selected)
        history_layout.addWidget(self.history)
        self.history_count = label("", "muted")
        history_layout.addWidget(self.history_count)
        split.addWidget(history_panel)

        story_panel, story_layout = panel("01  /  Письмо от «службы поддержки»")
        story_panel.setMinimumWidth(365)
        self.stage_label = label("", "badge")
        story_layout.addWidget(self.stage_label)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        story_body = QWidget()
        story_body_layout = QVBoxLayout(story_body)
        story_body_layout.setContentsMargins(0, 0, 4, 0)
        self.story_title = label("", "storyTitle")
        self.story_title.setObjectName("story_title")
        self.story_title.setStyleSheet("font-size: 23px; font-weight: 700;")
        story_body_layout.addWidget(self.story_title)
        self.story_description = label()
        self.story_description.setObjectName("story_description")
        story_body_layout.addWidget(self.story_description)
        self.actions = QVBoxLayout()
        self.actions.setSpacing(9)
        story_body_layout.addLayout(self.actions)
        story_body_layout.addStretch()
        scroll.setWidget(story_body)
        story_layout.addWidget(scroll)
        split.addWidget(story_panel)

        computer_panel, computer_layout = panel("Экран компьютера")
        computer_panel.setMinimumWidth(330)
        self.computer = VirtualComputer()
        computer_layout.addWidget(self.computer)
        split.addWidget(computer_panel)
        split.setSizes([290, 610, 430])
        layout.addWidget(split, 1)

        comparison_panel, comparison_layout = panel("Сравнение веток")
        self.comparison_toggle = QPushButton("Показать сравнение")
        self.comparison_toggle.setObjectName("toggle_comparison")
        self.comparison_toggle.setCheckable(True)
        comparison_heading = QHBoxLayout()
        comparison_heading.addWidget(comparison_layout.takeAt(0).widget())
        comparison_heading.addStretch()
        comparison_heading.addWidget(self.comparison_toggle)
        comparison_layout.addLayout(comparison_heading)
        self.comparison_body = QWidget()
        comparison_body_layout = QVBoxLayout(self.comparison_body)
        comparison_body_layout.setContentsMargins(0, 0, 0, 0)
        comparison_body_layout.setSpacing(12)
        comparison_layout.addWidget(self.comparison_body)
        selectors = QHBoxLayout()
        self.left_branch = QComboBox()
        self.left_branch.setObjectName("comparison_left")
        self.right_branch = QComboBox()
        self.right_branch.setObjectName("comparison_right")
        self.left_branch.setMinimumContentsLength(10)
        self.right_branch.setMinimumContentsLength(10)
        for name, combo in (("A", self.left_branch), ("B", self.right_branch)):
            selectors.addWidget(label(name, "badge", wrap=False))
            selectors.addWidget(combo, 1)
            combo.currentIndexChanged.connect(self._update_comparison)
        comparison_body_layout.addLayout(selectors)
        self.comparison = QTableWidget(5, 3)
        self.comparison.setObjectName("comparison_table")
        self.comparison.setHorizontalHeaderLabels(["Показатель", "Ветка A", "Ветка B"])
        self.comparison.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.comparison.verticalHeader().setVisible(False)
        self.comparison.verticalHeader().setDefaultSectionSize(25)
        self.comparison.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.comparison.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.comparison.setFixedHeight(160)
        comparison_body_layout.addWidget(self.comparison)
        self.comparison_body.setVisible(False)
        self.comparison_toggle.toggled.connect(self._toggle_comparison)
        layout.addWidget(comparison_panel)
        self.footer = label(
            "История сохраняется автоматически · "
            "Риск — учебная шкала, а не реальная оценка безопасности.",
            "muted",
        )
        layout.addWidget(self.footer)
        self._refresh()

    def _perform(self, action: Callable[[], object]) -> None:
        try:
            action()
            self._refresh()
        except (sqlite3.Error, ValueError, OSError) as error:
            QMessageBox.critical(self, "Не удалось сохранить решение", str(error))

    def _toggle_comparison(self, expanded: bool) -> None:
        self.comparison_body.setVisible(expanded)
        self.comparison_toggle.setText("Свернуть сравнение" if expanded else "Показать сравнение")

    def _choose(self, choice_id: str) -> None:
        self._perform(lambda: self.lab.choose(choice_id))

    def _history_selected(self) -> None:
        selected = self.history.selectedItems()
        if selected:
            entry_id = selected[0].data(0, Qt.ItemDataRole.UserRole)
            self._perform(lambda: self.lab.go_to(entry_id))

    def _return_to_start(self) -> None:
        root = next(entry for entry in self.lab.entries if entry.parent_id is None)
        self._perform(lambda: self.lab.go_to(root.id))

    def _refresh(self) -> None:
        entries = self.lab.entries
        self.entries_by_id = {entry.id: entry for entry in entries}
        active = self.lab.active
        self.story_title.setText(self.lab.node.title)
        self.story_description.setText(self.lab.node.description)
        self.stage_label.setText(
            "ИТОГ ВЕТКИ · можно вернуться назад" if self.lab.node.terminal else "ВАШЕ РЕШЕНИЕ"
        )
        while self.actions.count():
            item = self.actions.takeAt(0)
            widget = item.widget()
            widget.setParent(None)
            widget.deleteLater()
        for choice in self.lab.node.choices:
            button = QPushButton(f"{choice.title}\n{choice.hint}")
            button.setObjectName(f"choice_{choice.id}")
            button.setProperty("role", "choice")
            button.setToolTip(choice.hint)
            button.setMinimumHeight(60)
            button.clicked.connect(
                lambda _checked=False, choice_id=choice.id: self._choose(choice_id)
            )
            self.actions.addWidget(button)
        if self.lab.node.terminal:
            self.actions.addWidget(
                label(
                    "Выберите предыдущий шаг в истории слева, чтобы создать новую ветку.", "badge"
                )
            )
        state = active.state
        for widget, value in zip(
            self.metric_values,
            (
                f"{state.risk} / 100",
                "Раскрыты" if state.credentials_exposed else "Защищены",
                "Зашифрованы" if state.files_encrypted else "Доступны",
                "Подключена" if state.network_connected else "Отключена",
            ),
            strict=True,
        ):
            widget.setText(value)
        self.computer.render(state)
        self._render_history(entries)
        self._render_selectors(entries)
        if self.lab.node.terminal:
            self.comparison_toggle.setChecked(True)

    def _render_history(self, entries: list[HistoryEntry]) -> None:
        self.history.blockSignals(True)
        try:
            self.history.clear()
            items: dict[str, QTreeWidgetItem] = {}
            for index, entry in enumerate(entries, 1):
                ending = " · итог" if self.lab.scenario.node(entry.node_id).terminal else ""
                item = QTreeWidgetItem([f"{index:02d}  {entry.choice_title}{ending}"])
                item.setData(0, Qt.ItemDataRole.UserRole, entry.id)
                item.setToolTip(
                    0,
                    f"{self.lab.scenario.node(entry.node_id).title}\nРиск: {entry.state.risk}/100",
                )
                if entry.parent_id is None:
                    self.history.addTopLevelItem(item)
                else:
                    items[entry.parent_id].addChild(item)
                items[entry.id] = item
            self.history.expandAll()
            self.history.setCurrentItem(items[self.lab.active.id])
            self.history_count.setText(f"Сохранено шагов: {len(entries)} · SQLite")
        finally:
            self.history.blockSignals(False)

    def _render_selectors(self, entries: list[HistoryEntry]) -> None:
        previous_left = self.left_branch.currentData()
        alternatives = [
            entry
            for entry in entries
            if self.lab.scenario.node(entry.node_id).terminal and entry.id != self.lab.active.id
        ]
        left_id = previous_left if previous_left in self.entries_by_id else entries[0].id
        if self.lab.node.terminal and alternatives:
            left_id = alternatives[-1].id
        for combo, selected_id in (
            (self.left_branch, left_id),
            (self.right_branch, self.lab.active.id),
        ):
            combo.blockSignals(True)
            try:
                combo.clear()
                for index, entry in enumerate(entries, 1):
                    title = self.lab.scenario.node(entry.node_id).title
                    combo.addItem(f"{index:02d} · {entry.choice_title} → {title}", entry.id)
                combo.setCurrentIndex(combo.findData(selected_id))
            finally:
                combo.blockSignals(False)
        self._update_comparison()

    def _update_comparison(self) -> None:
        left = self.entries_by_id.get(self.left_branch.currentData())
        right = self.entries_by_id.get(self.right_branch.currentData())
        if left is None or right is None:
            return
        for row_index, row in enumerate(compare_states(left.state, right.state)):
            for column, text in enumerate((row.label, row.left, row.right)):
                item = QTableWidgetItem(text)
                if row.different:
                    item.setBackground(QColor("#203e37"))
                    item.setForeground(QColor("#a9f6d9"))
                self.comparison.setItem(row_index, column, item)
