"""Главное окно: собирает панели и передаёт действия пользователя в LabSession."""

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
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from cyberlab.domain import ComputerState, compare_states
from cyberlab.session import LabSession
from cyberlab.storage import HistoryEntry
from cyberlab.styles import STYLESHEET
from cyberlab.ui_helpers import create_label, create_panel
from cyberlab.virtual_computer import VirtualComputer


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
        header.addWidget(create_label("CYBERLAB", "brand", wrap=False))
        header.addWidget(
            create_label("Лаборатория решений\nИзучайте угрозы через последствия", "muted")
        )
        header.addStretch()
        header.addWidget(create_label("Локальная симуляция", "badge", wrap=False))
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
            box.addWidget(create_label(title, "muted"))
            value = create_label("", "metricValue", wrap=False)
            self.metric_values.append(value)
            box.addWidget(value)
            metrics.addWidget(frame, 0, index)
        layout.addLayout(metrics)

        split = QSplitter(Qt.Orientation.Horizontal)
        # В невысоком окне эти панели могут сжиматься: внутри уже есть прокрутка.
        # Так таблица сравнения остаётся целиком в своей панели.
        split.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Ignored)
        split.setChildrenCollapsible(False)
        history_panel, history_layout = create_panel("История решений")
        history_panel.setMinimumWidth(240)
        history_layout.addWidget(
            create_label("Выберите шаг и примите другое решение. Старые ветки сохранятся.", "muted")
        )
        self.history = QTreeWidget()
        self.history.setObjectName("decision_history")
        self.history.setHeaderHidden(True)
        self.history.setWordWrap(True)
        self.history.setIndentation(15)
        self.history.itemSelectionChanged.connect(self._history_selected)
        history_layout.addWidget(self.history)
        self.history_count = create_label("", "muted")
        history_layout.addWidget(self.history_count)
        split.addWidget(history_panel)

        story_panel, story_layout = create_panel(f"01  /  {self.lab.scenario.title}")
        story_panel.setMinimumWidth(365)
        self.stage_label = create_label("", "badge")
        story_layout.addWidget(self.stage_label)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        story_body = QWidget()
        story_body_layout = QVBoxLayout(story_body)
        story_body_layout.setContentsMargins(0, 0, 4, 0)
        self.story_title = create_label("", "storyTitle")
        self.story_title.setObjectName("story_title")
        self.story_title.setStyleSheet("font-size: 23px; font-weight: 700;")
        story_body_layout.addWidget(self.story_title)
        self.story_description = create_label()
        self.story_description.setObjectName("story_description")
        story_body_layout.addWidget(self.story_description)
        self.actions = QVBoxLayout()
        self.actions.setSpacing(9)
        story_body_layout.addLayout(self.actions)
        story_body_layout.addStretch()
        scroll.setWidget(story_body)
        story_layout.addWidget(scroll)
        split.addWidget(story_panel)

        computer_panel, computer_layout = create_panel("Экран компьютера")
        computer_panel.setMinimumWidth(330)
        self.computer = VirtualComputer()
        computer_layout.addWidget(self.computer)
        split.addWidget(computer_panel)
        split.setSizes([290, 610, 430])
        layout.addWidget(split, 1)

        comparison_panel, comparison_layout = create_panel("Сравнение веток")
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
            selectors.addWidget(create_label(name, "badge", wrap=False))
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
        self.footer = create_label(
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
        # Хранилище возвращает шаги в порядке создания: первый — корень истории.
        root_entry = self.lab.entries[0]
        self._perform(lambda: self.lab.go_to(root_entry.id))

    def _refresh(self) -> None:
        """Перерисовать панели по одному и тому же активному снимку."""
        entries = self.lab.entries
        self.entries_by_id = {entry.id: entry for entry in entries}
        active_entry = self.lab.active
        self.story_title.setText(self.lab.node.title)
        self.story_description.setText(self.lab.node.description)
        self.stage_label.setText(
            "ИТОГ ВЕТКИ · можно вернуться назад" if self.lab.node.terminal else "ВАШЕ РЕШЕНИЕ"
        )
        self._render_choices()
        self._render_metrics(active_entry.state)
        self.computer.render(active_entry.state)
        self._render_history(entries)
        self._render_selectors(entries)
        if self.lab.node.terminal:
            self.comparison_toggle.setChecked(True)

    def _render_choices(self) -> None:
        """Заменить кнопки прошлого шага вариантами текущего узла сценария."""
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
            # Сохраняем id в аргументе lambda. Без этого все кнопки цикла
            # ссылались бы на последнее значение переменной choice.
            button.clicked.connect(
                lambda _checked=False, choice_id=choice.id: self._choose(choice_id)
            )
            self.actions.addWidget(button)
        if self.lab.node.terminal:
            self.actions.addWidget(
                create_label(
                    "Выберите предыдущий шаг в истории слева, чтобы создать новую ветку.", "badge"
                )
            )

    def _render_metrics(self, state: ComputerState) -> None:
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

    def _render_history(self, entries: list[HistoryEntry]) -> None:
        # Выбор элемента порождает сигнал Qt. При восстановлении дерева сигнал
        # временно отключён, иначе _history_selected снова вызвал бы _refresh.
        self.history.blockSignals(True)
        try:
            self.history.clear()
            items_by_entry_id: dict[str, QTreeWidgetItem] = {}
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
                    # Родитель создан раньше ребёнка, поэтому уже есть в словаре.
                    items_by_entry_id[entry.parent_id].addChild(item)
                items_by_entry_id[entry.id] = item
            self.history.expandAll()
            self.history.setCurrentItem(items_by_entry_id[self.lab.active.id])
            self.history_count.setText(f"Сохранено шагов: {len(entries)} · SQLite")
        finally:
            self.history.blockSignals(False)

    def _render_selectors(self, entries: list[HistoryEntry]) -> None:
        """Предложить другой сохранённый итог для сравнения с текущей веткой."""
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
        left_entry = self.entries_by_id.get(self.left_branch.currentData())
        right_entry = self.entries_by_id.get(self.right_branch.currentData())
        if left_entry is None or right_entry is None:
            return
        for row_index, row in enumerate(compare_states(left_entry.state, right_entry.state)):
            for column, text in enumerate((row.label, row.left, row.right)):
                item = QTableWidgetItem(text)
                if row.different:
                    item.setBackground(QColor("#203e37"))
                    item.setForeground(QColor("#a9f6d9"))
                self.comparison.setItem(row_index, column, item)
        self.computer.render_comparison(left_entry.state, right_entry.state)
