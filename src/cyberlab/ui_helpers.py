"""Общие надписи, компактные действия и строки выбора."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
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
    layout.setContentsMargins(0, 12, 0, 12)
    layout.setSpacing(8)
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
    """Короткое действие. Второстепенное пояснение доступно при наведении."""
    button = QPushButton(title)
    button.setAccessibleName(title)
    button.setProperty("role", "primary" if primary else "secondary")
    button.setToolTip(hint)
    # Штатный QPushButton сам учитывает метрики шрифта и DPI платформы.
    # Вложенные надписи нужны только строкам выбора с двумя уровнями текста.
    button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    button.setMinimumHeight(32)
    return button


def link_button(title: str, hint: str = "") -> QPushButton:
    button = action_button(title, hint)
    button.setProperty("role", "link")
    return button


def choice_button(number: int, title: str, hint: str) -> QPushButton:
    """Варианты решения выглядят как строки списка, а не конкурирующие баннеры."""
    button = QPushButton()
    button.setAccessibleName(title)
    button.setToolTip(hint)
    button.setProperty("role", "decision")
    layout = QHBoxLayout(button)
    layout.setContentsMargins(12, 11, 12, 11)
    layout.setSpacing(14)
    number_label = create_label(f"{number:02d}", "choiceNumber", wrap=False)
    number_label.setFixedWidth(24)
    layout.addWidget(number_label)
    text = QVBoxLayout()
    text.setSpacing(3)
    text.addWidget(create_label(title, "buttonTitle"))
    text.addWidget(create_label(hint, "buttonHint"))
    layout.addLayout(text, 1)
    layout.addWidget(create_label("→", "choiceArrow", wrap=False))
    for label in button.findChildren(QLabel):
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
    return button


def clear_layout(layout: QVBoxLayout) -> None:
    """Убрать прежние карточки перед показом другого снимка."""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()
