"""Панель ИИ-наставника. Поток получает копию контекста, а не доступ к LabSession."""

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QPlainTextEdit, QProgressBar, QVBoxLayout, QWidget

from cyberlab.ai_client import MAX_QUESTION_CHARS, DeepSeekClient, MentorReply
from cyberlab.ai_context import MentorContext
from cyberlab.ui_helpers import action_button, create_label


class MentorRequest(QThread):
    reply_ready = Signal(object)

    def __init__(self, client: DeepSeekClient, context: MentorContext, task: str, question: str):
        super().__init__()
        self.client = client
        self.context = context
        self.task = task
        self.question = question

    def run(self) -> None:
        try:
            reply = self.client.answer(self.context, self.task, self.question)
        except Exception:
            reply = MentorReply(
                self.context.fallback(self.task), error="Ошибка ИИ. Показано локальное объяснение."
            )
        if not self.isInterruptionRequested():
            self.reply_ready.emit(reply)


class AiMentorPanel(QWidget):
    idle = Signal()

    def __init__(self, client: DeepSeekClient | None = None) -> None:
        super().__init__()
        self.client = client or DeepSeekClient()
        self.context: MentorContext | None = None
        self.worker: MentorRequest | None = None
        self.total_tokens = 0
        layout = QVBoxLayout(self)
        layout.addWidget(create_label("ИИ-наставник", "storyTitle"))
        self.mode = create_label("Локальный наставник — офлайн", "badge")
        layout.addWidget(self.mode)
        layout.addWidget(
            create_label(
                "Онлайн-запрос отправляет текущую учебную ситуацию и ваш вопрос в DeepSeek. "
                "Не вводите настоящие пароли, ключи и личные данные. "
                "Ответы ИИ могут содержать ошибки.",
                "muted",
            )
        )
        self.question = QPlainTextEdit()
        self.question.setPlaceholderText("Например: по каким признакам можно заметить фишинг?")
        self.question.setAcceptDrops(False)
        self.question.setMaximumHeight(100)
        self.question.textChanged.connect(self._limit_question)
        layout.addWidget(self.question)
        self.ask_button = action_button("Спросить ИИ", primary=True)
        self.decision_button = action_button("Объяснить моё решение")
        self.analysis_button = action_button("Проанализировать ошибки")
        self.compare_button = action_button("Сравнить выбранные варианты")
        self.buttons = [
            self.ask_button,
            self.decision_button,
            self.analysis_button,
            self.compare_button,
        ]
        for button, task in zip(
            self.buttons, ("question", "decision", "analysis", "comparison"), strict=True
        ):
            button.clicked.connect(lambda _checked=False, task=task: self.ask(task))
            layout.addWidget(button)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)
        self.status = create_label("Запрос выполняется только после нажатия кнопки.", "muted")
        layout.addWidget(self.status)
        self.answer = QPlainTextEdit()
        self.answer.setReadOnly(True)
        self.answer.setAcceptDrops(False)
        self.answer.setMinimumHeight(180)
        layout.addWidget(self.answer)
        self.usage = create_label("Статистика токенов пока не получена.", "muted")
        layout.addWidget(self.usage)
        self._enable_buttons()

    @property
    def busy(self) -> bool:
        return self.worker is not None

    def set_context(self, context: MentorContext) -> None:
        changed = self.context is None or self.context.key != context.key
        self.context = context
        if changed:
            self.mode.setText("Локальный наставник — офлайн")
            self.answer.setPlainText(context.local_state)
            self.status.setText("Ситуация обновлена. Новый запрос можно сделать по кнопке.")
            self.usage.setText(
                f"Получено токенов за сеанс: {self.total_tokens}. Новый ответ ещё не получен."
            )
        self._enable_buttons()

    def _limit_question(self) -> None:
        text = self.question.toPlainText()
        if len(text) > MAX_QUESTION_CHARS:
            self.question.setPlainText(text[:MAX_QUESTION_CHARS])

    def _enable_buttons(self) -> None:
        enabled = self.context is not None and not self.busy
        self.question.setEnabled(not self.busy)
        for button in self.buttons:
            button.setEnabled(enabled)
        self.compare_button.setEnabled(enabled and bool(self.context.local_comparison))
        self.compare_button.setToolTip(
            "Сначала откройте сравнение двух вариантов и затем ИИ-наставника."
        )

    def ask(self, task: str) -> None:
        if self.busy or self.context is None:
            return
        question = self.question.toPlainText().strip()
        if task == "question" and not question:
            self.status.setText("Сначала напишите вопрос по кибербезопасности.")
            return
        if task == "comparison" and not self.context.local_comparison:
            return
        self.worker = MentorRequest(
            self.client, self.context, task, question if task == "question" else ""
        )
        self.worker.reply_ready.connect(self._show_reply)
        self.worker.finished.connect(self._finished)
        self.progress.show()
        self.status.setText(
            "Ожидаем ответ наставника…"
            if self.client.configured
            else "Готовим локальное объяснение…"
        )
        self._enable_buttons()
        self.worker.start()

    def _show_reply(self, reply: MentorReply) -> None:
        if reply.usage is not None:
            self.total_tokens += reply.usage.total
        if self.context.key != self.worker.context.key:
            self.status.setText("Шаг или сравнение изменились. Ответ к прежнему шагу не показан.")
            self.usage.setText(f"Получено токенов за сеанс: {self.total_tokens}.")
            return
        self.mode.setText(
            "DeepSeek AI — онлайн" if reply.online else "Локальный наставник — офлайн"
        )
        self.answer.setPlainText(reply.text)
        self.status.setText(
            reply.error or "Ответ DeepSeek получен. Сверяйте его с результатами симуляции."
        )
        if reply.usage is not None:
            self.usage.setText(
                f"Токены: вход {reply.usage.prompt}, ответ {reply.usage.completion}, "
                f"всего {reply.usage.total}. За сеанс: {self.total_tokens}."
            )
        else:
            self.usage.setText(
                "Статистика запроса не получена. "
                f"Ранее получено токенов за сеанс: {self.total_tokens}."
            )

    def _finished(self) -> None:
        worker = self.worker
        self.worker = None
        worker.deleteLater()
        self.progress.hide()
        self._enable_buttons()
        self.idle.emit()

    def cancel_display(self) -> None:
        if self.worker is not None:
            self.worker.requestInterruption()
            self.status.setText(
                "Завершаем текущий запрос перед закрытием. Окно остаётся отзывчивым."
            )
