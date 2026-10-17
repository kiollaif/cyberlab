"""Три небольших помощника для повторяющихся элементов интерфейса."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


def create_label(text: str = "", name: str = "", *, wrap: bool = True) -> QLabel:
    """Создать текстовую надпись; имя используется в таблице стилей Qt."""
    widget = QLabel(text)
    widget.setObjectName(name)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(wrap)
    if wrap:
        # Длинный русский текст переносится, вместо расширения всего окна.
        widget.setMinimumWidth(0)
        widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
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
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    area.setWidget(widget)
    return area


def action_button(title: str, hint: str = "", *, primary: bool = False) -> QPushButton:
    """Кнопка с переносом строк: длинное действие остаётся читаемым при масштабе 150%."""
    button = QPushButton()
    button.setAccessibleName(title)
    button.setProperty("role", "primary" if primary else "secondary")
    layout = QVBoxLayout(button)
    layout.setContentsMargins(16, 12, 16, 12)
    layout.setSpacing(5)
    title_label = create_label(title, "buttonTitle")
    title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    layout.addWidget(title_label)
    if hint:
        hint_label = create_label(hint, "buttonHint")
        hint_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(hint_label)
    button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
    button.setMinimumHeight(48)
    return button


def clear_layout(layout: QVBoxLayout) -> None:
    """Убрать прежние карточки перед показом другого снимка."""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()
