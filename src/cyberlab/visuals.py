"""Небольшие интерактивные схемы средствами Qt: только сохранённые учебные данные."""

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class LineChart(QWidget):
    """Одна шкала 0–100. Нажатие точки открывает её фактическую подпись."""

    point_selected = Signal(int)

    def __init__(self, title: str) -> None:
        super().__init__()
        self.title = title
        self.values: tuple[int, ...] = ()
        self.labels: tuple[str, ...] = ()
        self.selected = -1
        self.setMinimumHeight(126)
        self.setMinimumWidth(0)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_values(self, values, labels=()) -> None:
        self.values = tuple(values)
        self.labels = tuple(labels)
        if self.labels and len(self.labels) != len(self.values):
            raise ValueError("Каждой точке нужна подпись.")
        if any(not 0 <= value <= 100 for value in self.values):
            raise ValueError("Значения диаграммы должны быть от 0 до 100.")
        self.selected = len(self.values) - 1
        summary = self.title + ": " + (" → ".join(map(str, self.values)) or "пока нет данных")
        self.setAccessibleName(summary)
        self.setToolTip(summary + ". Нажмите точку или используйте стрелки клавиатуры.")
        self.update()

    def point_position(self, index: int) -> QPointF:
        x = 36 + (self.width() - 56) * index / max(1, len(self.values) - 1)
        y = 30 + (self.height() - 54) * (100 - self.values[index]) / 100
        return QPointF(x, y)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor("#8d9aa9"))
        painter.drawText(0, 15, self.title)
        for value in (0, 50, 100):
            y = 30 + (self.height() - 54) * (100 - value) / 100
            painter.setPen(QColor("#29323e"))
            painter.drawLine(QPointF(32, y), QPointF(self.width() - 16, y))
            painter.setPen(QColor("#8998a8"))
            painter.drawText(QRectF(0, y - 8, 28, 18), Qt.AlignmentFlag.AlignLeft, str(value))
        if not self.values:
            painter.drawText(44, 70, "После завершения здесь появятся оценки.")
            return
        path = QPainterPath(self.point_position(0))
        for index in range(1, len(self.values)):
            path.lineTo(self.point_position(index))
        painter.setPen(QPen(QColor("#55cbd4"), 2))
        painter.drawPath(path)
        for index, value in enumerate(self.values):
            point = self.point_position(index)
            painter.setBrush(QColor("#55cbd4" if index == self.selected else "#121a24"))
            painter.drawEllipse(point, 4, 4)
            painter.setPen(QColor("#d3e2ef"))
            painter.drawText(
                QRectF(point.x() - 18, point.y() - 22, 36, 18),
                Qt.AlignmentFlag.AlignCenter,
                str(value),
            )
            painter.setPen(QPen(QColor("#55cbd4"), 2))

    def _select(self, index: int) -> None:
        if not self.values:
            return
        self.selected = max(0, min(len(self.values) - 1, index))
        self.point_selected.emit(self.selected)
        self.update()

    def mousePressEvent(self, event) -> None:
        if self.values:
            index = min(
                range(len(self.values)),
                key=lambda i: abs(self.point_position(i).x() - event.position().x()),
            )
            self._select(index)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            self._select(self.selected + (1 if event.key() == Qt.Key.Key_Right else -1))
        else:
            super().keyPressEvent(event)


class ConsequenceMap(QWidget):
    """Три факта: ситуация → выбор → состояние. Узлы раскрываются без смены снимка."""

    selected = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.items: tuple[str, ...] = ()
        self.active = 2
        self.setMinimumHeight(96)
        self.setMinimumWidth(0)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Выберите узел схемы мышью или стрелками клавиатуры.")

    def set_facts(self, situation: str, decision: str, consequence: str) -> None:
        self.items = (situation, decision, consequence)
        self.active = 2
        self.setAccessibleName(" → ".join(self.items))
        self.update()

    def node_rect(self, index: int) -> QRectF:
        gap = 18
        width = (self.width() - 2 * gap) / 3
        return QRectF(index * (width + gap), 6, width, 82)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for index, title in enumerate(("Ситуация", "Ваш выбор", "Последствие")):
            rect = self.node_rect(index)
            painter.setBrush(QColor("#152733" if index == self.active else "#141c26"))
            painter.setPen(QColor("#55cbd4" if index == self.active else "#2a3949"))
            painter.drawRoundedRect(rect, 6, 6)
            painter.setPen(QColor("#8ba5bb"))
            painter.drawText(rect.adjusted(10, 6, -8, -50), Qt.AlignmentFlag.AlignLeft, title)
            if self.items:
                # Полный текст доступен по нажатию, поэтому схема остаётся компактной.
                text = painter.fontMetrics().elidedText(
                    self.items[index], Qt.TextElideMode.ElideRight, max(0, int(rect.width() - 20))
                )
                painter.setPen(QColor("#d8e4ef"))
                painter.drawText(rect.adjusted(10, 38, -8, -8), Qt.AlignmentFlag.AlignLeft, text)
            if index < 2:
                painter.drawText(
                    QRectF(rect.right(), 35, 18, 24), Qt.AlignmentFlag.AlignCenter, "→"
                )

    def _select(self, index: int) -> None:
        if self.items:
            self.active = max(0, min(2, index))
            self.selected.emit(self.items[self.active])
            self.update()

    def mousePressEvent(self, event) -> None:
        for index in range(3):
            if self.node_rect(index).contains(event.position()):
                self._select(index)
                break

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            self._select(self.active + (1 if event.key() == Qt.Key.Key_Right else -1))
        else:
            super().keyPressEvent(event)
