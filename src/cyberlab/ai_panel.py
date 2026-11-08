"""Панель ИИ-наставника. Поток получает копию контекста, а не доступ к LabSession."""

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QPlainTextEdit,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from cyberlab.ai_client import MAX_QUESTION_CHARS, DeepSeekClient, MentorReply
from cyberlab.ai_context import MentorContext
from cyberlab.glossary import TERMS
from cyberlab.ui_helpers import action_button, create_label, link_button


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
        layout.setSpacing(14)
        heading = QHBoxLayout()
        heading.addWidget(create_label("Помощник CyberLab", "storyTitle"), 1)
        self.mode = create_label("Локальный наставник — офлайн", "muted")
        self.mode.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        heading.addWidget(self.mode, 1)
        layout.addLayout(heading)
        layout.addWidget(
            create_label(
                "Локальный помощник — система на правилах и проверенная справка, не нейросеть. "
                "Работает без интернета и оплаты. Онлайн-ответы доступны только при "
                "подключённом сервисе.",
                "muted",
            )
        )
        self.term_selector = QComboBox()
        self.term_selector.setAccessibleName("Объяснить термин без интернета")
        self.term_selector.addItem("Объяснить термин без интернета…")
        self.term_selector.addItems(list(TERMS))
        self.term_selector.activated.connect(self._explain_term)
        layout.addWidget(self.term_selector)
        self.answer = QPlainTextEdit()
        self.answer.setProperty("role", "answer")
        self.answer.setReadOnly(True)
        self.answer.setAcceptDrops(False)
        self.answer.setMinimumHeight(220)
        layout.addWidget(self.answer, 1)
        tools = QHBoxLayout()
        tools.setSpacing(4)
        self.decision_button = link_button("Объяснить выбор")
        self.analysis_button = link_button("Разобрать ошибки")
        self.compare_button = link_button("Сравнить варианты")
        for button in (self.decision_button, self.analysis_button, self.compare_button):
            tools.addWidget(button)
        tools.addStretch()
        layout.addLayout(tools)
        self.question = QPlainTextEdit()
        self.question.setPlaceholderText(
            "Вопрос по учебной ситуации. Не вводите настоящие пароли и личные данные."
        )
        self.question.setAcceptDrops(False)
        self.question.setFixedHeight(76)
        self.question.textChanged.connect(self._limit_question)
        layout.addWidget(self.question)
        send_row = QHBoxLayout()
        send_row.addWidget(create_label("До 1000 символов", "caption"))
        send_row.addStretch()
        self.ask_button = action_button("Задать вопрос", primary=True)
        send_row.addWidget(self.ask_button)
        layout.addLayout(send_row)
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
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedHeight(2)
        self.progress.hide()
        layout.addWidget(self.progress)
        self.status = create_label("", "muted")
        self.status.hide()
        layout.addWidget(self.status)
        self.usage = create_label("", "caption")
        self.usage.setToolTip(
            "Токены — части текста, которыми сервис измеряет объём запроса и ответа."
        )
        self.usage_toggle = link_button("Статистика ответа")
        self.usage_toggle.setCheckable(True)
        self.usage_toggle.toggled.connect(self.usage.setVisible)
        self.usage_toggle.hide()
        layout.addWidget(self.usage_toggle, alignment=Qt.AlignmentFlag.AlignLeft)
        self.usage.hide()
        layout.addWidget(self.usage)
        self._enable_buttons()

    @property
    def busy(self) -> bool:
        return self.worker is not None

    def _explain_term(self, index: int) -> None:
        if index > 0 and not self.busy:
            self.answer.setPlainText(TERMS[self.term_selector.itemText(index)])
            self.mode.setText("Локальный наставник — офлайн")
            self.status.setText("Объяснение из локальной справки. Сеть не использовалась.")
            self.status.show()

    def set_context(self, context: MentorContext) -> None:
        changed = self.context is None or self.context.key != context.key
        self.context = context
        if changed:
            self.mode.setText("Локальный наставник — офлайн")
            self.answer.setPlainText(context.local_state)
            self.status.hide()
            self.usage.setText(f"Токенов за сеанс: {self.total_tokens}.")
            self.usage_toggle.setVisible(self.total_tokens > 0)
            self.usage_toggle.setChecked(False)
            self.usage.hide()
        self._enable_buttons()

    def _limit_question(self) -> None:
        text = self.question.toPlainText()
        if len(text) > MAX_QUESTION_CHARS:
            self.question.setPlainText(text[:MAX_QUESTION_CHARS])

    def _enable_buttons(self) -> None:
        enabled = self.context is not None and not self.busy
        self.question.setEnabled(not self.busy)
        self.term_selector.setEnabled(not self.busy)
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
            self.status.show()
            return
        if task == "comparison" and not self.context.local_comparison:
            return
        self.worker = MentorRequest(
            self.client, self.context, task, question if task == "question" else ""
        )
        self.worker.reply_ready.connect(self._show_reply)
        self.worker.finished.connect(self._finished)
        self.progress.show()
        self.status.show()
        self.status.setText(
            "Ожидаем ответ наставника…"
            if self.client.configured
            else "Готовим локальное объяснение…"
        )
        self._enable_buttons()
        self.worker.start()

    def _show_reply(self, reply: MentorReply) -> None:
        self.status.show()
        if reply.usage is not None:
            self.total_tokens += reply.usage.total
        if self.context.key != self.worker.context.key:
            self.status.setText("Шаг или сравнение изменились. Ответ к прежнему шагу не показан.")
            self.usage.setText(f"Получено токенов за сеанс: {self.total_tokens}.")
            return
        self.mode.setText(
            f"{getattr(self.client, 'display_name', 'DeepSeek AI')} — онлайн"
            if reply.online
            else "Локальный наставник — офлайн"
        )
        self.answer.setPlainText(reply.text)
        if not self.client.configured and not getattr(self.client, "configuration_error", ""):
            # Отсутствие платного сервиса — нормальный режим, а не ошибка ученика.
            self.status.setText("Ответ локального помощника. Интернет и оплата не требуются.")
        else:
            self.status.setText(
                reply.error or "Ответ наставника получен. Сверяйте его с результатами тренировки."
            )
        if reply.usage is not None:
            self.usage.setText(
                f"Токены: вход {reply.usage.prompt}, ответ {reply.usage.completion}, "
                f"всего {reply.usage.total}. За сеанс: {self.total_tokens}."
            )
            self.usage_toggle.show()
        else:
            self.usage.setText(
                "Статистика запроса не получена. "
                f"Ранее получено токенов за сеанс: {self.total_tokens}."
            )
            self.usage_toggle.setVisible(self.total_tokens > 0 or self.client.configured)
        self.usage.setVisible(self.usage_toggle.isChecked() and not self.usage_toggle.isHidden())

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
            self.status.show()
            self.status.setText(
                "Завершаем текущий запрос перед закрытием. Окно остаётся отзывчивым."
            )
