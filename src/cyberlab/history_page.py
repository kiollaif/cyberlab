"""История результатов: фильтр тем, реальные оценки и открытие выбранного варианта."""

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from cyberlab.domain import Scenario
from cyberlab.statistics import ResultRecord
from cyberlab.ui_helpers import action_button, create_label
from cyberlab.visuals import LineChart


class HistoryPage(QWidget):
    open_requested = Signal()
    start_requested = Signal()

    def __init__(self, scenarios: tuple[Scenario, ...]) -> None:
        super().__init__()
        self.scenarios = {scenario.id: scenario for scenario in scenarios}
        self.records: list[ResultRecord] = []
        self.chart_records: list[ResultRecord] = []
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.addWidget(create_label("История результатов", "storyTitle"))
        layout.addWidget(
            create_label(
                "Откройте прежний результат или продолжите незавершённую тренировку.", "muted"
            )
        )
        self.filter = QComboBox()
        self.filter.setAccessibleName("Показать результаты темы")
        self.filter.addItem("Все темы", "")
        for scenario in scenarios:
            self.filter.addItem(scenario.title, scenario.id)
        self.filter.currentIndexChanged.connect(self._fill)
        layout.addWidget(self.filter)
        self.summary = create_label("", "heading")
        layout.addWidget(self.summary)
        self.chart = LineChart("Оценка решений по времени · 0–100")
        self.chart.point_selected.connect(self._select_chart_point)
        layout.addWidget(self.chart)
        self.point_detail = create_label(
            "Нажмите точку диаграммы, чтобы выбрать результат.", "muted"
        )
        layout.addWidget(self.point_detail)
        self.list = QListWidget()
        self.list.setWordWrap(True)
        self.list.setAccessibleName("Сохранённые результаты и тренировки")
        self.list.setMinimumHeight(190)
        self.list.itemDoubleClicked.connect(lambda _item: self.open_requested.emit())
        layout.addWidget(self.list)
        self.empty = create_label("Пока нет решений. Начните первую симуляцию.", "muted")
        layout.addWidget(self.empty)
        self.start_button = action_button("Начать симуляцию", primary=True)
        self.start_button.clicked.connect(self.start_requested.emit)
        layout.addWidget(self.start_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.open_button = action_button("Открыть выбранный результат", primary=True)
        self.open_button.clicked.connect(self.open_requested.emit)
        layout.addWidget(self.open_button, alignment=Qt.AlignmentFlag.AlignLeft)

    def render(self, records: list[ResultRecord]) -> None:
        self.records = records
        self._fill()

    def _fill(self) -> None:
        scenario_id = self.filter.currentData()
        filtered = [
            item for item in self.records if not scenario_id or item.scenario_id == scenario_id
        ]
        completed = [item for item in filtered if item.completed]
        best = max((item.score for item in completed if item.score is not None), default=None)
        self.summary.setText(
            f"Завершённых вариантов: {len(completed)} · "
            + (
                f"Лучшая оценка: {best}/100"
                if best is not None
                else "Оценки появятся после завершения"
            )
        )
        self.chart_records = list(reversed(completed[:12]))
        self.chart.set_values([item.score for item in self.chart_records])
        self.chart.setVisible(bool(completed))
        self.point_detail.setVisible(bool(completed))
        self.point_detail.setText(
            "Последние 12 завершённых вариантов. Нажмите точку для просмотра."
        )
        self.list.clear()
        for record in filtered:
            date = datetime.fromisoformat(record.created_at).astimezone().strftime("%d.%m.%Y %H:%M")
            status = "Завершено" if record.completed else "В процессе"
            score = f" · Оценка {record.score}/100" if record.completed else ""
            item = QListWidgetItem(
                f"{self.scenarios[record.scenario_id].title}\n"
                f"{status} · {date}{score} · Риск {record.risk}/100 · Решений: {record.decisions}"
            )
            item.setToolTip(
                f"{record.title}. Безопасных: {record.safe}; рискованных: {record.risky}."
            )
            item.setData(Qt.ItemDataRole.UserRole, record.session_id)
            item.setData(Qt.ItemDataRole.UserRole + 1, record.scenario_id)
            item.setData(Qt.ItemDataRole.UserRole + 2, record.entry_id)
            self.list.addItem(item)
        empty = not filtered
        self.empty.setVisible(empty)
        self.start_button.setVisible(empty)
        self.list.setVisible(not empty)
        self.open_button.setVisible(not empty)
        self.open_button.setEnabled(not empty)
        self.list.setCurrentRow(0)

    def _select_chart_point(self, index: int) -> None:
        record = self.chart_records[index]
        self.point_detail.setText(
            f"{self.scenarios[record.scenario_id].title}: оценка {record.score}/100; "
            f"риск {record.risk}/100. {record.title}."
        )
        for row in range(self.list.count()):
            if self.list.item(row).data(Qt.ItemDataRole.UserRole + 2) == record.entry_id:
                self.list.setCurrentRow(row)
                self.list.scrollToItem(self.list.item(row))
                break
