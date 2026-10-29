"""Компактная боковая навигация. Значки рисуются средствами Qt без новых пакетов."""

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget

from cyberlab.ui_helpers import create_label


def navigation_icon(name: str, color: str = "#9999a5") -> QIcon:
    pixmap = QPixmap(36, 36)
    pixmap.fill(Qt.GlobalColor.transparent)
    pixmap.setDevicePixelRatio(2)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(color), 1.25, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    if name == "home":
        for x in (3, 10):
            for y in (3, 10):
                painter.drawRoundedRect(QRectF(x, y, 5, 5), 1, 1)
    elif name == "simulation":
        path = QPainterPath(QPointF(6, 3))
        path.lineTo(14, 9)
        path.lineTo(6, 15)
        path.closeSubpath()
        painter.drawPath(path)
    elif name == "decisions":
        painter.drawLine(5, 3, 5, 14)
        painter.drawLine(5, 9, 13, 5)
        for x, y in ((5, 3), (5, 14), (13, 5)):
            painter.drawEllipse(QPointF(x, y), 1.6, 1.6)
    elif name == "comparison":
        painter.drawRoundedRect(QRectF(2, 3, 5, 12), 1, 1)
        painter.drawRoundedRect(QRectF(11, 3, 5, 12), 1, 1)
    elif name == "sessions":
        painter.drawEllipse(QRectF(3, 3, 12, 12))
        painter.drawLine(9, 5, 9, 9)
        painter.drawLine(9, 9, 12, 11)
    elif name == "computer":
        painter.drawRoundedRect(QRectF(2, 3, 14, 10), 1.5, 1.5)
        painter.drawLine(9, 13, 9, 16)
        painter.drawLine(6, 16, 12, 16)
    elif name == "mentor":
        painter.drawRoundedRect(QRectF(2, 3, 14, 10), 2, 2)
        painter.drawLine(5, 13, 5, 16)
        painter.drawLine(5, 16, 9, 13)
        painter.drawLine(6, 7, 12, 7)
        painter.drawLine(6, 10, 10, 10)
    else:
        painter.drawEllipse(QRectF(3, 3, 12, 12))
        painter.drawText(QRectF(3, 2, 12, 13), Qt.AlignmentFlag.AlignCenter, "?")
    painter.end()
    return QIcon(pixmap)


class WorkspaceNavigation(QWidget):
    navigate = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("sidebar")
        self.compact = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 24, 14, 18)
        layout.setSpacing(4)
        self.brand = create_label("CYBERLAB", "brand", wrap=False)
        layout.addWidget(self.brand)
        self.caption = create_label("Практикум безопасности", "sidebarCaption")
        layout.addWidget(self.caption)
        layout.addSpacing(30)
        self.buttons = {}
        self.titles = {
            "home": "Обзор",
            "simulation": "Симуляция",
            "decisions": "Ваши решения",
            "comparison": "Сравнение",
            "sessions": "Прохождения",
            "computer": "Компьютер",
            "mentor": "Наставник",
            "help": "Как это работает",
        }
        for name, title in self.titles.items():
            if name == "computer":
                layout.addSpacing(22)
            if name == "help":
                layout.addStretch()
            button = QPushButton(title)
            button.setAccessibleName(title)
            button.setObjectName(f"nav_{name}")
            button.setProperty("role", "nav")
            button.setIcon(navigation_icon(name))
            button.setIconSize(QSize(18, 18))
            button.setCheckable(True)
            button.setMinimumHeight(34)
            button.setToolTip(title)
            button.clicked.connect(lambda _checked=False, name=name: self.navigate.emit(name))
            layout.addWidget(button)
            self.buttons[name] = button
        layout.addSpacing(12)
        self.footer = create_label("Версия 0.1", "sidebarCaption")
        layout.addWidget(self.footer)
        self.setFixedWidth(202)

    def select(self, selected: str) -> None:
        for name, button in self.buttons.items():
            button.setChecked(name == selected)
            button.setIcon(navigation_icon(name, "#cecbf1" if name == selected else "#9999a5"))

    def set_compact(self, compact: bool) -> None:
        if compact == self.compact:
            return
        self.compact = compact
        self.setFixedWidth(60 if compact else 202)
        self.brand.setText("C" if compact else "CYBERLAB")
        self.caption.setVisible(not compact)
        self.footer.setVisible(not compact)
        self.layout().setContentsMargins(8 if compact else 14, 24, 8 if compact else 14, 18)
        for name, button in self.buttons.items():
            button.setText("" if compact else self.titles[name])
