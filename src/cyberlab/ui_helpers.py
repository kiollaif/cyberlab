"""Три небольших помощника для повторяющихся элементов интерфейса."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QScrollArea, QVBoxLayout, QWidget


def create_label(text: str = "", name: str = "", *, wrap: bool = True) -> QLabel:
    """Создать текстовую надпись; имя используется в таблице стилей Qt."""
    widget = QLabel(text)
    widget.setObjectName(name)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(wrap)
    return widget


def create_panel(title: str) -> tuple[QFrame, QVBoxLayout]:
    """Вернуть панель и её вертикальную раскладку для добавления содержимого."""
    frame = QFrame()
    frame.setObjectName("panel")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(12)
    layout.addWidget(create_label(title, "heading"))
    return frame, layout


def make_scrollable(widget: QWidget) -> QScrollArea:
    """Добавить прокрутку, если содержимое не помещается на небольшом экране."""
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(widget)
    return area
