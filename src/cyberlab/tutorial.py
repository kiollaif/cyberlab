"""Пять коротких шагов обучения. Демонстрация не создаёт решений в SQLite."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from cyberlab.ui_helpers import action_button, create_label, create_panel, link_button

LESSONS = (
    (
        "Что такое фишинг",
        "Это обманное сообщение или сайт. Его цель — убедить вас передать данные "
        "или выполнить опасное действие. В CyberLab можно ошибаться без вреда настоящему ПК.",
        "Пример: «Ваш доступ закроют через 15 минут. Подтвердите пароль по ссылке». "
        "Срочность помогает обманщику торопить человека.",
    ),
    (
        "Как программа попадает на устройство",
        "Неизвестный установщик, вложение или USB могут содержать опасный код. "
        "Загрузка файла и разрешение запуска — разные действия.",
        "Пример: файл скачан, но не открыт. Отмена запуска ещё может остановить выполнение. "
        "В симуляторе эти события меняют только учебное состояние.",
    ),
    (
        "Проверьте адрес, а не только имя",
        "Отображаемое имя и картинку можно скопировать. Сравните адрес с известным "
        "и уточните неожиданную просьбу другим способом. Попробуйте кнопку ниже.",
        "Пример: имя «Поддержка школы», но адрес help@school-check.invalid. "
        "Известный школьный сайт — school.example. Адреса не совпадают.",
    ),
    (
        "Не разрешайте неизвестному файлу команды",
        "Макрос — команды внутри документа. Не включайте их неожиданному файлу "
        "и не отключайте защиту ради сомнительного установщика.",
        "Пример: документ обещает показать расписание только после включения макросов. "
        "Лучше проверить отправителя через известный контакт.",
    ),
    (
        "Ваш выбор меняет историю",
        "Читайте ситуацию → выбирайте действие → разбирайте последствие. "
        "Сверху видно, сколько решений осталось. Риск 0–100 — учебная шкала, а не проверка ПК.",
        "В итогах можно изменить решение и сравнить два пути. Прежний результат сохранится. "
        "Во время прохождения возврат находится в «Инструментах» → «Ваши решения».",
    ),
)


class TutorialPage(QWidget):
    finished = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.step = 0
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        self.progress = create_label("", "eyebrow")
        self.title = create_label("", "storyTitle")
        self.description = create_label("", "muted")
        layout.addWidget(self.progress)
        layout.addWidget(self.title)
        layout.addWidget(self.description)
        panel, contents = create_panel("Так это выглядит")
        panel.setObjectName("scenarioRow")
        contents.setContentsMargins(0, 18, 0, 18)
        self.example = create_label()
        contents.addWidget(self.example)
        self.practice_button = action_button("Проверить отправителя")
        self.practice_button.clicked.connect(self._practice)
        contents.addWidget(self.practice_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(panel)
        controls = QHBoxLayout()
        self.previous_button = link_button("Назад")
        self.previous_button.clicked.connect(lambda: self._move(-1))
        self.next_button = action_button("Далее", primary=True)
        self.next_button.clicked.connect(lambda: self._move(1))
        self.finish_button = action_button("На главную", primary=True)
        self.finish_button.clicked.connect(self.finished.emit)
        controls.addWidget(self.previous_button)
        controls.addWidget(self.next_button)
        controls.addWidget(self.finish_button)
        controls.addStretch()
        self.skip_button = link_button("Пропустить подсказки")
        self.skip_button.clicked.connect(self.finished.emit)
        controls.addWidget(self.skip_button)
        layout.addLayout(controls)
        layout.addStretch()
        self.render()

    def reset(self) -> None:
        self.step = 0
        self.render()

    def _practice(self) -> None:
        self.example.setText(
            "Вы запросили сведения и увидели адрес отправителя. "
            "Теперь есть больше информации для решения. Нажмите «Далее»."
        )
        self.practice_button.setEnabled(False)

    def _move(self, direction: int) -> None:
        self.step = max(0, min(len(LESSONS) - 1, self.step + direction))
        self.render()

    def render(self) -> None:
        title, description, example = LESSONS[self.step]
        self.progress.setText(f"Как это работает · {self.step + 1} из {len(LESSONS)}")
        self.title.setText(title)
        self.description.setText(description)
        self.example.setText(example)
        self.previous_button.setEnabled(self.step > 0)
        self.next_button.setVisible(self.step < len(LESSONS) - 1)
        self.finish_button.setVisible(self.step == len(LESSONS) - 1)
        self.practice_button.setVisible(self.step == 2)
        self.practice_button.setEnabled(True)
