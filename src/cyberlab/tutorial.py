"""Пять коротких шагов обучения. Демонстрация не создаёт решений в SQLite."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from cyberlab.ui_helpers import action_button, create_label, create_panel, link_button

LESSONS = (
    (
        "Добро пожаловать в CYBERLAB",
        "Здесь вы учитесь распознавать угрозы на вымышленном компьютере. "
        "Можно ошибаться: настоящий компьютер и файлы в безопасности.",
        "Ситуация → Выбор → Последствие → Следующая ситуация",
    ),
    (
        "Сначала прочитайте ситуацию",
        "На экране будет одна текущая задача. Сверху — название этапа и прогресс. "
        "Сначала узнайте, что произошло, затем выбирайте действие.",
        "Пример ситуации: пришло сообщение от незнакомого отправителя.",
    ),
    (
        "Выберите действие",
        "Строки под ситуацией — ваши варианты. Попробуйте учебное действие ниже. "
        "Этот пример не влияет на прохождение.",
        "Одно нажатие — одно решение. Следующий выбор появится после объяснения.",
    ),
    (
        "Разберите последствие",
        "После выбора вы увидите, что случилось, почему и как изменился риск. "
        "Кнопка «Следующая ситуация» откроет следующий этап. Подробности компьютера необязательны.",
        "Пример: запросили сведения → получили адрес отправителя. Риск: 0 → 0. "
        "Сама проверка ничего не передаёт неизвестному отправителю.",
    ),
    (
        "Попробуйте иначе и сравните",
        "Откройте «Инструменты» → «Ваши решения» слева и нажмите «На шаг назад». Вы вернётесь "
        "к выбору перед последним действием. Любой более ранний шаг доступен в дереве. "
        "Для сравнения откройте раздел «Сравнение».",
        "Начало\n├─ Первый выбор → сохранённый результат\n└─ Другой выбор → новый результат\n"
        "Обе ветки сохраняются даже после закрытия программы.",
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
