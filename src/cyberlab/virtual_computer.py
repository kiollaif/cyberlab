"""Только отображение виртуального ПК: почта, файлы, журнал и браузер."""

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QListWidget, QTabWidget, QTextEdit, QVBoxLayout, QWidget

from cyberlab.domain import VIRTUAL_FILES, ComputerState
from cyberlab.mentor import explain_comparison, explain_state
from cyberlab.ui_helpers import create_label, make_scrollable


class VirtualComputer(QWidget):
    """Экран учебного ПК. Ни один виджет не открывает внешние адреса или файлы."""

    def __init__(self) -> None:
        super().__init__()
        self.state = ComputerState()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        heading = create_label("Учебный компьютер", "storyTitle")
        heading.setToolTip("Почта, файлы и сеть существуют только внутри модели.")
        layout.addWidget(heading)
        self.notification = create_label("", "muted")
        self.notification.hide()
        layout.addWidget(self.notification)
        self.tabs = QTabWidget()
        self.tabs.setObjectName("computer_tabs")
        self.tabs.setUsesScrollButtons(True)
        layout.addWidget(self.tabs)

        mail = QWidget()
        mail_layout = QVBoxLayout(mail)
        mail_layout.setContentsMargins(0, 20, 0, 0)
        mail_layout.setSpacing(14)
        self.mail_status = create_label("", "caption")
        self.mail_status.setObjectName("mail_status")
        mail_layout.addWidget(self.mail_status)
        mail_layout.addWidget(create_label("Срочно подтвердите пароль", "heading"))
        mail_layout.addWidget(
            create_label("От: IT-поддержка · Кому: сотрудник@cyberlab.example", "muted")
        )
        mail_layout.addWidget(
            create_label(
                "Ваш пароль истекает через 15 минут. Подтвердите учётную запись, "
                "чтобы сохранить доступ к проекту."
            )
        )
        link = create_label("Текст ссылки: «Подтвердить учётную запись»", "muted")
        link.setToolTip("Действия с письмом выбираются в разделе «Симуляция».")
        mail_layout.addWidget(link)
        self.mail_details = create_label("", "muted")
        self.mail_details.setObjectName("mail_details")
        mail_layout.addWidget(self.mail_details)
        mail_layout.addStretch()
        self.tabs.addTab(make_scrollable(mail), "Почта")

        files = QWidget()
        files_layout = QVBoxLayout(files)
        files_layout.addWidget(create_label("Выберите файл для просмотра.", "muted"))
        self.file_list = QListWidget()
        self.file_list.setObjectName("virtual_files")
        self.file_list.addItems([file.name for file in VIRTUAL_FILES])
        self.file_list.setMaximumHeight(115)
        self.file_content = QTextEdit()
        self.file_content.setObjectName("file_content")
        self.file_content.setReadOnly(True)
        self.file_content.setAcceptRichText(False)
        files_layout.addWidget(self.file_list)
        files_layout.addWidget(self.file_content)
        self.file_list.currentRowChanged.connect(self._show_file)
        self.file_list.setCurrentRow(0)
        self.tabs.addTab(files, "Файлы")

        self.journal = QListWidget()
        self.journal.setObjectName("event_journal")
        self.journal.setWordWrap(True)
        journal_page = QWidget()
        journal_layout = QVBoxLayout(journal_page)
        journal_layout.addWidget(create_label("События выбранного пути", "muted"))
        journal_layout.addWidget(self.journal)
        self.tabs.addTab(journal_page, "Журнал")

        browser = QWidget()
        browser_layout = QVBoxLayout(browser)
        browser_layout.addWidget(create_label("Страница, открытая внутри сценария.", "muted"))
        self.browser_status = create_label()
        self.browser_status.setObjectName("browser_status")
        browser_layout.addWidget(self.browser_status)
        self.browser_page = QWidget()
        page_layout = QVBoxLayout(self.browser_page)
        page_layout.addWidget(create_label("login.cyberlab-check.invalid", "badge"))
        page_layout.addWidget(create_label("Подтвердите учётную запись", "heading"))
        page_layout.addWidget(
            create_label(
                "Это макет поддельной страницы. Настоящая сеть не используется. "
                "Отправка вымышленного пароля моделируется выбором решения на экране ситуации."
            )
        )
        browser_layout.addWidget(self.browser_page)
        browser_layout.addStretch()
        self.tabs.addTab(make_scrollable(browser), "Браузер")

        mentor_panel = QWidget()
        mentor_layout = QVBoxLayout(mentor_panel)
        mentor_layout.addWidget(create_label("Учебный наставник", "heading"))
        mentor_layout.addWidget(
            create_label(
                "Локальные объяснения текущего состояния.",
                "muted",
            )
        )
        self.mentor_state = create_label()
        self.mentor_state.setObjectName("mentor_state")
        mentor_layout.addWidget(self.mentor_state)
        mentor_layout.addWidget(create_label("Последнее выбранное сравнение", "heading"))
        self.mentor_comparison = create_label()
        self.mentor_comparison.setObjectName("mentor_comparison")
        self.mentor_comparison.setText("Сравнение доступно в итогах и в разделе «Ваши решения».")
        mentor_layout.addWidget(self.mentor_comparison)
        mentor_layout.addStretch()
        self.tabs.addTab(make_scrollable(mentor_panel), "Наставник")

    def render(self, state: ComputerState) -> None:
        previous_state = self.state
        self.state = state
        if state != previous_state:
            self._highlight_changes(previous_state, state)
            self.mentor_comparison.setText(
                "Сравнение доступно в итогах и в разделе «Ваши решения»."
            )
        self.mentor_state.setText(explain_state(state))
        self.mail_status.setText(
            "КАРАНТИН · письмо изолировано" if state.email_quarantined else "ВХОДЯЩИЕ · 1 письмо"
        )
        self.mail_details.setText(
            "От: help@cyberlab-support.invalid\n"
            "Ссылка: https://login.cyberlab-check.invalid\n"
            "Ожидаемый домен: cyberlab.example"
            if state.email_inspected
            else "Адрес отправителя скрыт за отображаемым именем. Выберите «Проверить письмо»."
        )
        self.journal.clear()
        self.journal.addItems(list(state.events))
        self.browser_status.setText(
            "Страница открыта" if state.browser_open else "Страница закрыта"
        )
        self.browser_page.setVisible(state.browser_open)
        self._show_file(self.file_list.currentRow())
        # При новом последствии показываем связанную вкладку. При простом
        # обновлении того же снимка выбранная пользователем вкладка не сбрасывается.
        if state.files_encrypted and not previous_state.files_encrypted:
            self.tabs.setCurrentIndex(1)
        elif state.browser_open and not previous_state.browser_open:
            self.tabs.setCurrentIndex(3)
        elif not state.browser_open and previous_state.browser_open:
            self.tabs.setCurrentIndex(0)

    def _highlight_changes(self, before: ComputerState, after: ComputerState) -> None:
        changed_tabs = {2}
        notices = []
        if before.files_encrypted != after.files_encrypted:
            changed_tabs.add(1)
            notices.append(
                "Файлы стали недоступны в симуляции. Настоящие файлы не затронуты."
                if after.files_encrypted
                else "Снова открыт снимок с доступными файлами."
            )
        if before.credentials_exposed != after.credentials_exposed:
            notices.append(
                "Учебный пароль раскрыт на чужой странице."
                if after.credentials_exposed
                else "В этом снимке пароль ещё не раскрыт."
            )
        if before.browser_open != after.browser_open:
            changed_tabs.add(3)
        if (before.email_inspected, before.email_quarantined) != (
            after.email_inspected,
            after.email_quarantined,
        ):
            changed_tabs.add(0)
        self.notification.setText("\n".join(notices) or after.events[-1])
        self.notification.show()
        for index, title in enumerate(("Почта", "Файлы", "Журнал", "Браузер", "Наставник")):
            changed = index in changed_tabs
            self.tabs.setTabText(index, title + (" •" if changed else ""))
            self.tabs.setTabToolTip(index, "Изменилось в текущем снимке" if changed else title)
            self.tabs.tabBar().setTabTextColor(index, QColor("#cecbf1" if changed else "#92929d"))

    def _show_file(self, row: int) -> None:
        if row < 0:
            return
        file = VIRTUAL_FILES[row]
        self.file_content.setPlainText(
            f"{file.name}\n\n[Содержимое недоступно]\n"
            "Файл зашифрован в учебной модели. Вернитесь к предыдущему решению, "
            "чтобы восстановить снимок."
            if self.state.files_encrypted
            else file.content
        )

    def render_comparison(self, left: ComputerState, right: ComputerState) -> None:
        self.mentor_comparison.setText(explain_comparison(left, right))
