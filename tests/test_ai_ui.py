import threading

import pytest
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QPushButton

from cyberlab.ai_client import DeepSeekClient, MentorReply, TokenUsage
from cyberlab.session import LabSession
from cyberlab.storage import HistoryRepository
from cyberlab.ui import MainWindow


@pytest.fixture
def window(qtbot, tmp_path):
    repository = HistoryRepository(tmp_path / "ai.sqlite3")
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    settings.setValue("tutorial_completed", True)
    widget = MainWindow(LabSession(repository), settings)
    widget.ai_mentor.client = DeepSeekClient(api_key="")
    qtbot.addWidget(widget)
    widget.show()
    widget.start_button.click()
    yield widget
    qtbot.waitUntil(lambda: not widget.ai_mentor.busy, timeout=5000)
    widget.close()
    repository.close()


def open_decision_mentor(window):
    window.situation.findChild(QPushButton, "choice_open_link").click()
    window.ai_buttons[window.consequence].click()
    assert window.current_page is window.ai_mentor


class SlowClient:
    configured = True

    def __init__(self):
        self.entered = threading.Event()
        self.release = threading.Event()
        self.calls = []
        self.thread_id = None

    def answer(self, context, task, question):
        self.thread_id = threading.get_ident()
        self.calls.append((context, task, question))
        self.entered.set()
        if not self.release.wait(3):
            raise TimeoutError("test worker timed out")
        return MentorReply("Ответ о старом выборе", online=True, usage=TokenUsage(10, 5, 15))


def test_background_request_does_not_freeze_ui_or_duplicate_or_write_database(qtbot, window):
    client = SlowClient()
    window.ai_mentor.client = client
    open_decision_mentor(window)
    panel = window.ai_mentor
    before = window.lab.entries
    ticks = []
    timer = QTimer(window)
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start(10)
    try:
        assert not client.calls  # навигация сама не отправляет запрос
        panel.decision_button.click()
        qtbot.waitUntil(client.entered.is_set)
        panel.ask("decision")  # защита и от прямого повторного события
        panel.analysis_button.click()
        qtbot.waitUntil(lambda: len(ticks) >= 3)
        assert len(client.calls) == 1
        assert client.thread_id != threading.get_ident()
        assert panel.progress.isVisible() and not panel.ask_button.isEnabled()
        client.release.set()
        qtbot.waitUntil(lambda: not panel.busy)
        assert panel.mode.text() == "DeepSeek AI — онлайн"
        assert "старом выборе" in panel.answer.toPlainText()
        assert "всего 15" in panel.usage.text()
        assert window.lab.entries == before
    finally:
        client.release.set()
        qtbot.waitUntil(lambda: not panel.busy)
        timer.stop()


def test_no_key_uses_local_mentor_and_scenario_still_works(qtbot, window):
    open_decision_mentor(window)
    panel = window.ai_mentor
    panel.decision_button.click()
    qtbot.waitUntil(lambda: not panel.busy)
    assert panel.mode.text() == "Локальный наставник — офлайн"
    assert "не задан" in panel.status.text()
    assert "чужой домен" in panel.answer.toPlainText()
    window.back_button.click()
    window.consequence.continue_button.click()
    window.situation.findChild(QPushButton, "choice_close_report").click()
    window.consequence.continue_button.click()
    assert window.current_page is window.results
    assert not window.lab.active.state.credentials_exposed


def test_rewind_discards_a_reply_for_an_old_context(qtbot, window):
    client = SlowClient()
    window.ai_mentor.client = client
    root_id = window.lab.active.id
    open_decision_mentor(window)
    panel = window.ai_mentor
    try:
        panel.decision_button.click()
        qtbot.waitUntil(client.entered.is_set)
        window._go_to(root_id)
        client.release.set()
        qtbot.waitUntil(lambda: not panel.busy)
        assert "старом выборе" not in panel.answer.toPlainText()
        assert "не показан" in panel.status.text()
        assert panel.mode.text() == "Локальный наставник — офлайн"
        assert window.lab.active.id == root_id
    finally:
        client.release.set()
        qtbot.waitUntil(lambda: not panel.busy)


def test_close_waits_for_thread_without_blocking_event_loop(qtbot, window):
    client = SlowClient()
    window.ai_mentor.client = client
    open_decision_mentor(window)
    panel = window.ai_mentor
    try:
        panel.decision_button.click()
        qtbot.waitUntil(client.entered.is_set)
        window.close()
        assert window.isVisible()
        assert "перед закрытием" in panel.status.text()
        client.release.set()
        qtbot.waitUntil(lambda: not panel.busy)
        qtbot.waitUntil(lambda: not window.isVisible())
    finally:
        client.release.set()
        qtbot.waitUntil(lambda: not panel.busy)


def test_comparison_is_only_sent_after_explicit_request(qtbot, window):
    root = window.lab.active.id
    window.lab.choose("open_link")
    window.lab.choose("submit")
    window.lab.choose("ignore")
    window.lab.go_to(root)
    window.lab.choose("report")
    window._display_active()
    window.results.compare_button.click()
    window.ai_buttons[window.comparison].click()
    panel = window.ai_mentor
    assert panel.compare_button.isEnabled()
    assert "comparison" in panel.context.payload
    panel.compare_button.click()
    qtbot.waitUntil(lambda: not panel.busy)
    assert "риск ниже" in panel.answer.toPlainText()


def test_question_limit_empty_question_and_plain_text(qtbot, window):
    open_decision_mentor(window)
    panel = window.ai_mentor
    panel.ask_button.click()
    assert not panel.busy and "напишите вопрос" in panel.status.text()
    panel.question.setPlainText("x" * 1200)
    assert len(panel.question.toPlainText()) == 1000
    panel.answer.setPlainText("<script>Это простой текст</script>")
    assert "<script>" in panel.answer.toPlainText()
