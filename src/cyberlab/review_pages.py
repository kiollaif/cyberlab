"""Просмотр дерева и сравнение сохранённых веток. Выбор сравнения не меняет игру."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from cyberlab.domain import Scenario, compare_states
from cyberlab.learning import history_path, state_summary
from cyberlab.mentor import explain_decision
from cyberlab.simulation_pages import StateOverview
from cyberlab.storage import HistoryEntry
from cyberlab.ui_helpers import action_button, create_label, create_panel


class DecisionsPage(QWidget):
    entry_requested = Signal(str)
    alternative_requested = Signal()
    root_requested = Signal()
    compare_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(create_label("Ваши решения", "storyTitle"))
        layout.addWidget(
            create_label(
                "Вы можете вернуться к предыдущему выбору и попробовать другой вариант. "
                "Старый результат сохранится."
            )
        )
        self.alternative_button = action_button("Попробовать другой вариант", primary=True)
        self.alternative_button.clicked.connect(self.alternative_requested.emit)
        layout.addWidget(self.alternative_button)
        self.tree = QTreeWidget()
        self.tree.setObjectName("decision_history")
        self.tree.setHeaderHidden(True)
        self.tree.setWordWrap(True)
        self.tree.setIndentation(18)
        self.tree.setMinimumHeight(240)
        self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tree.currentItemChanged.connect(self._selection_changed)
        layout.addWidget(self.tree, 1)
        self.preview = create_label("", "badge")
        layout.addWidget(self.preview)
        self.open_button = action_button("Вернуться к выбранному шагу")
        self.open_button.clicked.connect(self._open_selected)
        layout.addWidget(self.open_button)
        controls = QHBoxLayout()
        self.root_button = action_button("К началу сценария")
        self.root_button.clicked.connect(self.root_requested.emit)
        self.compare_button = action_button("Сравнить сохранённые шаги")
        self.compare_button.clicked.connect(self.compare_requested.emit)
        controls.addWidget(self.root_button)
        controls.addWidget(self.compare_button)
        layout.addLayout(controls)

    def render(self, scenario: Scenario, entries: list[HistoryEntry], active: HistoryEntry) -> None:
        self.entries_by_id = {entry.id: entry for entry in entries}
        self.scenario = scenario
        self.tree.blockSignals(True)
        self.tree.clear()
        items = {}
        for entry in entries:
            title = "Получено письмо · начало" if entry.parent_id is None else entry.choice_title
            if scenario.node(entry.node_id).terminal:
                title += " · итог"
            if entry.id == active.id:
                title += " ← вы здесь"
            item = QTreeWidgetItem([title])
            item.setData(0, Qt.ItemDataRole.UserRole, entry.id)
            item.setToolTip(0, f"{title}\nРиск: {entry.state.risk}/100")
            if entry.id == active.id:
                font = QFont()
                font.setBold(True)
                item.setFont(0, font)
            if entry.parent_id is None:
                self.tree.addTopLevelItem(item)
            else:
                items[entry.parent_id].addChild(item)
            items[entry.id] = item
        self.tree.expandAll()
        self.tree.setCurrentItem(items[active.id])
        self.tree.scrollToItem(items[active.id])
        self.tree.blockSignals(False)
        self.alternative_button.setEnabled(active.parent_id is not None)
        self._selection_changed()

    def _selection_changed(self) -> None:
        item = self.tree.currentItem()
        if item is None:
            return
        entry = self.entries_by_id[item.data(0, Qt.ItemDataRole.UserRole)]
        self.preview.setText(
            f"{self.scenario.node(entry.node_id).title}\n{state_summary(entry.state)}\n"
            "Нажмите «Вернуться к выбранному шагу», чтобы открыть этот снимок."
        )

    def _open_selected(self) -> None:
        item = self.tree.currentItem()
        if item is not None:
            self.entry_requested.emit(item.data(0, Qt.ItemDataRole.UserRole))


class ComparisonPage(QWidget):
    states_selected = Signal(object, object)

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(create_label("Сравнение результатов", "storyTitle"))
        layout.addWidget(
            create_label(
                "Выберите два сохранённых варианта. Здесь можно сравнить и разные ветки, "
                "и отдельные прохождения. Текущий шаг от этого не изменится."
            )
        )
        self.include_steps = QCheckBox("Показать также промежуточные состояния")
        self.include_steps.toggled.connect(self._fill_selectors)
        layout.addWidget(self.include_steps, alignment=Qt.AlignmentFlag.AlignLeft)
        self.hint = create_label("", "badge")
        layout.addWidget(self.hint)
        self.selectors = []
        self.overviews = []
        self.metric_labels = []
        self.routes = []
        self.routes_body = QWidget()
        routes_layout = QGridLayout(self.routes_body)
        routes_layout.setContentsMargins(0, 0, 0, 0)
        columns = QGridLayout()
        self.card_grid = columns
        self.route_grid = routes_layout
        self.card_panels = []
        self.route_panels = []
        self._narrow = None
        for index, title in enumerate(("Первый вариант", "Второй вариант")):
            panel, contents = create_panel(title)
            combo = QComboBox()
            combo.setObjectName(f"comparison_{'left' if index == 0 else 'right'}")
            combo.setMinimumContentsLength(15)
            # У Windows минимальная ширина списка зависит от системного шрифта.
            # Разрешаем двум спискам сжиматься вместе с карточками; полный текст
            # выбранного пункта остаётся в подсказке и в разборе пути.
            combo.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            combo.setSizeAdjustPolicy(
                QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
            )
            combo.currentIndexChanged.connect(self._update_comparison)
            contents.addWidget(combo)
            self.selectors.append(combo)
            overview = StateOverview(compact=True)
            contents.addWidget(overview)
            self.overviews.append(overview)
            metrics = [overview.risk] + [create_label() for _ in range(4)]
            for label in metrics[1:]:
                contents.addWidget(label)
            self.metric_labels.append(metrics)
            route_panel, route_layout = create_panel(f"{title}: решения по порядку")
            self.card_panels.append(panel)
            self.route_panels.append(route_panel)
            route = create_label()
            route_layout.addWidget(route)
            route_layout.addStretch()
            routes_layout.addWidget(route_panel, 0, index)
            routes_layout.setColumnStretch(index, 1)
            self.routes.append(route)
            contents.addStretch()
            columns.addWidget(panel, 0, index)
            columns.setColumnStretch(index, 1)
        layout.addLayout(columns)
        self.divergence = create_label("", "heading")
        self.conclusion = create_label("", "badge")
        layout.addWidget(self.divergence)
        layout.addWidget(self.conclusion)
        self.details_toggle = action_button("Показать решения и объяснения")
        self.details_toggle.setCheckable(True)
        self.details_toggle.toggled.connect(self.routes_body.setVisible)
        layout.addWidget(self.details_toggle)
        layout.addWidget(self.routes_body)
        self.routes_body.hide()
        layout.addStretch()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        narrow = self.width() < 760
        if narrow == self._narrow:
            return
        self._narrow = narrow
        # На узком экране две карточки идут друг под другом: системный шрифт
        # Windows может требовать больше места, чем два столбца по 280 пикселей.
        for grid, panels in (
            (self.card_grid, self.card_panels),
            (self.route_grid, self.route_panels),
        ):
            grid.setColumnStretch(1, 0 if narrow else 1)
            for index, panel in enumerate(panels):
                grid.addWidget(panel, index if narrow else 0, 0 if narrow else index)

    def render(
        self,
        scenario: Scenario,
        entries: list[HistoryEntry],
        session_numbers: dict[str, int],
        active: HistoryEntry,
    ) -> None:
        self.scenario = scenario
        self.entries = entries
        self.entries_by_id = {entry.id: entry for entry in entries}
        self.session_numbers = session_numbers
        self.active_id = active.id
        self.details_toggle.setChecked(False)
        endings = [entry for entry in entries if scenario.node(entry.node_id).terminal]
        self.include_steps.blockSignals(True)
        self.include_steps.setChecked(not endings or not scenario.node(active.node_id).terminal)
        self.include_steps.blockSignals(False)
        self.include_steps.setEnabled(bool(endings))
        self._fill_selectors()

    def _fill_selectors(self) -> None:
        available = [
            entry
            for entry in self.entries
            if self.include_steps.isChecked() or self.scenario.node(entry.node_id).terminal
        ]
        if not available:
            return
        others = [entry for entry in available if entry.id != self.active_id]
        defaults = [others[-1].id if others else available[0].id, self.active_id]
        for index, combo in enumerate(self.selectors):
            combo.blockSignals(True)
            combo.clear()
            for entry in available:
                kind = "Итог" if self.scenario.node(entry.node_id).terminal else "Шаг"
                number = self.session_numbers[entry.session_id]
                text = f"Прохождение {number} · {kind}: {entry.choice_title}"
                combo.addItem(text, entry.id)
                combo.setItemData(combo.count() - 1, text, Qt.ItemDataRole.ToolTipRole)
            combo.setCurrentIndex(max(0, combo.findData(defaults[index])))
            combo.blockSignals(False)
        self.hint.setText(
            "Сохранён пока один результат. Измените решение и завершите другую ветку "
            "или включите промежуточные состояния."
            if len(available) == 1
            else "Различия отмечены словом «Отличается» и цветом. "
            "Одинаковый риск не означает одинаковый путь."
        )
        self._update_comparison()

    def _update_comparison(self) -> None:
        selected = [combo.currentData() for combo in self.selectors]
        if any(entry_id is None for entry_id in selected):
            return
        left, right = [self.entries_by_id[entry_id] for entry_id in selected]
        rows = compare_states(left.state, right.state)
        paths = [history_path(self.entries, entry.id) for entry in (left, right)]
        for column, entry in enumerate((left, right)):
            self.overviews[column].render(entry.state)
            self.selectors[column].setToolTip(self.selectors[column].currentText())
            for label, row in zip(self.metric_labels[column], rows, strict=True):
                value = row.left if column == 0 else row.right
                label.setText(f"{row.label}: {value}" + (" · Отличается" if row.different else ""))
                label.setStyleSheet("color: #efc18e;" if row.different else "")
            steps = []
            path = paths[column]
            for before, after in zip(path, path[1:], strict=False):
                steps.append(
                    f"{len(steps) + 1}. {after.choice_title} "
                    f"(риск {before.state.risk} → {after.state.risk})\n"
                    + explain_decision(after.choice_id, before.state, after.state)
                )
            self.routes[column].setText("\n\n".join(steps) or "Начало: решений ещё нет.")
        self.divergence.setText(self._describe_divergence(paths[0], paths[1]))
        self.conclusion.setText(
            f"В первом случае: {state_summary(left.state)}\n\n"
            f"Во втором случае: {state_summary(right.state)}"
        )
        self.states_selected.emit(left.state, right.state)

    @staticmethod
    def _describe_divergence(left: list[HistoryEntry], right: list[HistoryEntry]) -> str:
        for first, second in zip(left[1:], right[1:], strict=False):
            if first.choice_id != second.choice_id:
                return (
                    f"Пути разошлись при выборе: «{first.choice_title}» в первом варианте "
                    f"и «{second.choice_title}» во втором. "
                    "Откройте разбор решений, чтобы увидеть дальнейшие шаги."
                )
        if len(left) != len(right):
            return "Один путь продолжает другой: сравниваются разные этапы, а не два разных выбора."
        return "Последовательности решений совпадают. Можно выбрать другой сохранённый вариант."
