"""Первый запуск и выбор темы. На главном экране нет инструментов симулятора."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QVBoxLayout, QWidget

from cyberlab.scenarios import SCENARIOS
from cyberlab.ui_helpers import action_button, create_label, link_button


class HomePage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.addStretch(1)
        layout.addWidget(create_label("CYBERLAB", "welcomeBrand"))
        layout.addWidget(
            create_label("Интерактивный тренажёр кибербезопасности", "welcomeSubtitle")
        )
        layout.addWidget(
            create_label(
                "Вы будете принимать решения в ситуациях, связанных с интернет-безопасностью, "
                "и узнавать, к каким последствиям они приводят.",
                "welcomeDescription",
            )
        )
        layout.addSpacing(16)
        self.start_button = action_button("Начать обучение", primary=True)
        self.resume_button = action_button("Продолжить")
        self.results_button = action_button("Мои результаты")
        for button in (self.start_button, self.resume_button, self.results_button):
            button.setProperty("size", "welcome")
            button.setMinimumHeight(46)
            button.setMinimumWidth(240)
            layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.resume_hint = create_label("", "muted")
        layout.addWidget(self.resume_hint)
        self.help_button = link_button("Как это работает?")
        layout.addWidget(self.help_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(2)


class TrainingPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        layout.addWidget(create_label("С чего начнём?", "storyTitle"))
        layout.addWidget(
            create_label(
                "Выберите тему. Затем прочитайте ситуацию и решите, как поступить.", "muted"
            )
        )
        layout.addSpacing(8)
        label = create_label("Тема обучения", "heading")
        layout.addWidget(label)
        self.selector = QComboBox()
        self.selector.setAccessibleName("Тема обучения")
        self.selector.setMinimumHeight(44)
        label.setBuddy(self.selector)
        for scenario in SCENARIOS:
            self.selector.addItem(scenario.title, scenario.id)
        layout.addWidget(self.selector)
        self.description = create_label("", "welcomeDescription")
        layout.addWidget(self.description)
        layout.addWidget(
            create_label(
                "Это безопасная тренировка. Настоящие файлы и устройства не изменятся.", "muted"
            )
        )
        layout.addSpacing(12)
        self.start_button = action_button("Начать тренировку", primary=True)
        self.start_button.setObjectName("start_simulation")
        layout.addWidget(self.start_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.resume_button = link_button("Продолжить эту тему")
        layout.addWidget(self.resume_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.progress_hint = create_label("", "muted")
        layout.addWidget(self.progress_hint)
        layout.addStretch()
