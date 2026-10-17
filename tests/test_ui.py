import os
import subprocess
import sys

import pytest
from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtWidgets import QLabel, QMessageBox, QPushButton

from cyberlab.session import LabSession
from cyberlab.storage import HistoryRepository
from cyberlab.ui import MainWindow


@pytest.fixture
def window(qtbot, tmp_path):
    repo = HistoryRepository(tmp_path / "ui.sqlite3")
    settings = QSettings(str(tmp_path / "preferences.ini"), QSettings.Format.IniFormat)
    settings.setValue("tutorial_completed", True)
    widget = MainWindow(LabSession(repo), settings)
    qtbot.addWidget(widget)
    widget.resize(1280, 720)
    widget.show()
    qtbot.waitUntil(widget.isVisible)
    yield widget
    widget.close()
    repo.close()


def click(qtbot, window, button):
    window.pages[window.current_page].ensureWidgetVisible(button)
    qtbot.waitUntil(button.isVisible)
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)


def start(qtbot, window):
    click(qtbot, window, window.start_button)
    assert window.current_page is window.situation


def choose(qtbot, window, choice_id, *, proceed=True):
    assert window.current_page is window.situation
    button = window.situation.findChild(QPushButton, f"choice_{choice_id}")
    assert button is not None
    click(qtbot, window, button)
    assert window.current_page is window.consequence
    assert not window.situation.isVisible()
    if proceed:
        click(qtbot, window, window.consequence.continue_button)


def open_decisions(qtbot, window):
    page = window.current_page
    button = (
        window.results.change_button
        if page is window.results
        else window.situation.decisions_button
    )
    click(qtbot, window, button)
    assert window.current_page is window.decisions


def test_first_menu_tutorial_skip_and_replay_do_not_write_decisions(qtbot, window):
    window.settings.setValue("tutorial_completed", False)
    assert window.current_page is window.menu
    assert not window.resume_button.isVisible()
    original = window.lab.entries
    click(qtbot, window, window.sessions_button)
    assert window.empty_history.isVisible()
    assert not window.open_session_button.isEnabled()
    click(qtbot, window, window.back_button)
    click(qtbot, window, window.start_button)
    assert window.current_page is window.tutorial
    for _ in range(2):
        click(qtbot, window, window.tutorial.next_button)
    click(qtbot, window, window.tutorial.practice_button)
    assert "увидели адрес" in window.tutorial.example.text()
    assert window.lab.entries == original
    click(qtbot, window, window.tutorial.skip_button)
    assert window.current_page is window.situation
    assert window.settings.value("tutorial_completed", type=bool)
    click(qtbot, window, window.menu_button)
    click(qtbot, window, window.help_button)
    assert window.tutorial.step == 0
    for _ in range(4):
        click(qtbot, window, window.tutorial.next_button)
    click(qtbot, window, window.tutorial.finish_button)
    assert window.current_page is window.menu
    assert window.lab.entries == original
    start(qtbot, window)  # обучение больше не включается автоматически


def test_gui_exercises_attack_rewind_alternative_and_comparison(qtbot, window):
    start(qtbot, window)
    root_id = window.lab.active.id
    choose(qtbot, window, "open_link", proceed=False)
    assert "0 → 30" in window.consequence.risk_change.text()
    assert "ещё не передало пароль" in window.consequence.reason.text()
    assert not window.comparison.isVisible()
    click(qtbot, window, window.consequence.details_button)
    assert window.computer.tabs.currentIndex() == 3
    assert window.computer.browser_page.isVisible()
    click(qtbot, window, window.back_button)
    assert window.current_page is window.consequence
    click(qtbot, window, window.consequence.continue_button)
    choose(qtbot, window, "submit")
    choose(qtbot, window, "ignore")
    damage = window.lab.active
    assert window.current_page is window.results
    assert "100 / 100" in window.results.overview.risk.text()
    assert "Содержимое недоступно" in window.computer.file_content.toPlainText()
    assert window.computer.journal.count() == 4
    assert "Файлы стали недоступны" in window.computer.notification.text()
    assert "вместо" in window.results.alternatives.text().lower()
    assert not window.comparison.isVisible()

    open_decisions(qtbot, window)
    assert "вы здесь" in window.decisions.tree.currentItem().text(0)
    window.decisions.tree.setCurrentItem(window.decisions.tree.topLevelItem(0))
    assert window.lab.active == damage  # предварительный просмотр ещё не перемещает указатель
    click(qtbot, window, window.decisions.open_button)
    assert window.lab.active.id == root_id
    assert "Учебный бюджет" in window.computer.file_content.toPlainText()
    choose(qtbot, window, "report")
    safe = window.lab.active
    assert "карантин" in window.computer.mail_status.text().lower()
    assert len(window.lab.entries) == 5
    click(qtbot, window, window.results.compare_button)
    assert window.current_page is window.comparison
    assert not window.comparison.include_steps.isChecked()
    left, right = window.comparison.selectors
    assert left.currentData() == damage.id
    assert right.currentData() == safe.id
    assert "100 / 100" in window.comparison.metric_labels[0][0].text()
    assert "0 / 100" in window.comparison.metric_labels[1][0].text()
    assert "Зашифрованы" in window.comparison.metric_labels[0][2].text()
    assert "Доступны" in window.comparison.metric_labels[1][2].text()
    assert "Открыть ссылку" in window.comparison.divergence.text()
    assert "Сообщить" in window.comparison.divergence.text()
    assert "В первом случае" in window.comparison.conclusion.text()
    assert not window.comparison.routes_body.isVisible()
    click(qtbot, window, window.comparison.details_toggle)
    assert window.comparison.routes_body.isVisible()
    assert "Отправить учебный пароль" in window.comparison.routes[0].text()
    assert "Отправить учебный пароль" not in window.comparison.routes[1].text()
    assert window.lab.active == safe
    click(qtbot, window, window.back_button)
    open_decisions(qtbot, window)
    assert window.decisions.tree.topLevelItem(0).childCount() == 2


def test_inspection_reveals_addresses_and_back_button_preserves_branch(qtbot, window):
    start(qtbot, window)
    choose(qtbot, window, "inspect")
    assert "help@cyberlab-support.invalid" in window.computer.mail_details.text()
    inspected = window.lab.active
    open_decisions(qtbot, window)
    click(qtbot, window, window.decisions.alternative_button)
    assert window.lab.active.parent_id is None
    assert not window.lab.active.state.email_inspected
    choose(qtbot, window, "inspect")
    assert window.lab.active == inspected
    assert len(window.lab.entries) == 2
    open_decisions(qtbot, window)
    click(qtbot, window, window.decisions.root_button)
    assert window.lab.active.parent_id is None
    assert len(window.lab.entries) == 2


def test_comparison_selectors_do_not_move_active_history(qtbot, window):
    start(qtbot, window)
    choose(qtbot, window, "open_link")
    opened = window.lab.active
    choose(qtbot, window, "close_report")
    active = window.lab.active
    click(qtbot, window, window.results.compare_button)
    assert "один результат" in window.comparison.hint.text()
    click(qtbot, window, window.comparison.include_steps)
    assert window.comparison.include_steps.isChecked()
    left, right = window.comparison.selectors
    left.setCurrentIndex(left.findData(window.lab.entries[0].id))
    right.setCurrentIndex(right.findData(opened.id))
    assert "0 / 100" in window.comparison.metric_labels[0][0].text()
    assert "30 / 100" in window.comparison.metric_labels[1][0].text()
    assert "продолжает другой" in window.comparison.divergence.text()
    assert window.lab.active == active


def test_comparison_before_any_ending_and_alternative_from_consequence(qtbot, window):
    start(qtbot, window)
    choose(qtbot, window, "inspect", proceed=False)
    inspected = window.lab.active
    click(qtbot, window, window.consequence.alternative_button)
    assert window.lab.active.parent_id is None
    open_decisions(qtbot, window)
    click(qtbot, window, window.decisions.compare_button)
    assert window.comparison.include_steps.isChecked()
    assert not window.comparison.include_steps.isEnabled()
    assert window.comparison.selectors[0].count() == 2
    assert window.comparison.selectors[0].currentData() == inspected.id
    assert window.lab.active.parent_id is None


def test_mentor_follows_rewind_and_independent_comparison(qtbot, window):
    start(qtbot, window)
    click(qtbot, window, window.situation.mentor_toggle)
    assert "зашифрован" not in window.situation.mentor.text()
    choose(qtbot, window, "open_link")
    assert not window.situation.mentor.isVisible()
    choose(qtbot, window, "submit")
    choose(qtbot, window, "ignore")
    damage_id = window.lab.active.id
    assert "Виртуальные файлы зашифрованы" in window.computer.mentor_state.text()
    open_decisions(qtbot, window)
    click(qtbot, window, window.decisions.root_button)
    assert "риск: 0/100" in window.computer.mentor_state.text()
    choose(qtbot, window, "report")
    safe = window.lab.active
    click(qtbot, window, window.results.compare_button)
    assert "риск ниже" in window.computer.mentor_comparison.text()
    left, right = window.comparison.selectors
    left.setCurrentIndex(left.findData(safe.id))
    right.setCurrentIndex(right.findData(damage_id))
    assert "риск выше" in window.computer.mentor_comparison.text()
    assert "риск: 0/100" in window.computer.mentor_state.text()
    assert window.lab.active == safe


def test_saved_sessions_can_be_reopened_and_compared(qtbot, window):
    start(qtbot, window)
    choose(qtbot, window, "report")
    first_session = window.lab.session.id
    safe = window.lab.active
    click(qtbot, window, window.results.retry_button)
    assert window.current_page is window.situation
    assert window.lab.session.id != first_session
    choose(qtbot, window, "open_link")
    choose(qtbot, window, "submit")
    choose(qtbot, window, "isolate")
    isolated = window.lab.active
    click(qtbot, window, window.results.compare_button)
    assert {combo.currentData() for combo in window.comparison.selectors} == {safe.id, isolated.id}
    click(qtbot, window, window.menu_button)
    click(qtbot, window, window.sessions_button)
    assert window.session_list.count() == 2
    window.session_list.setCurrentRow(1)
    click(qtbot, window, window.open_session_button)
    assert window.lab.active == safe
    assert window.current_page is window.results
    assert len(window.lab.repository.sessions(window.lab.scenario.id)) == 2
    assert window.settings.value("last_session") == first_session


def test_started_training_can_resume_before_first_choice(qtbot, window):
    start(qtbot, window)
    original_session = window.lab.session.id
    click(qtbot, window, window.menu_button)
    assert window.resume_button.isVisible()
    click(qtbot, window, window.resume_button)
    assert window.current_page is window.situation
    assert window.lab.session.id == original_session
    assert len(window.lab.entries) == 1


def test_gui_restart_shows_saved_state(qtbot, tmp_path):
    path = tmp_path / "restart.sqlite3"
    preferences = str(tmp_path / "settings.ini")
    repo = HistoryRepository(path)
    lab = LabSession(repo)
    lab.choose("open_link")
    lab.choose("submit")
    isolated = lab.choose("isolate")
    original_entries = lab.entries
    # Продолжаем более старую тренировку, даже если новая создана позже.
    original_session_id = lab.session.id
    lab.new_session()
    lab.choose("report")
    repo.close()
    settings = QSettings(preferences, QSettings.Format.IniFormat)
    settings.setValue("last_session", original_session_id)
    repo = HistoryRepository(path)
    try:
        widget = MainWindow(LabSession(repo), settings)
        qtbot.addWidget(widget)
        widget.show()
        assert widget.current_page is widget.menu
        assert widget.resume_button.isVisible()
        click(qtbot, widget, widget.resume_button)
        assert widget.current_page is widget.results
        assert "Ущерб ограничен" in widget.results.title.text()
        assert "Сеть: отключена" in widget.results.overview.status.text()
        assert widget.computer.journal.count() == 4
        assert widget.lab.entries == original_entries
        assert widget.lab.active == isolated
        widget.close()
    finally:
        repo.close()


def test_restart_restores_unread_consequence(qtbot, window):
    start(qtbot, window)
    choose(qtbot, window, "open_link", proceed=False)
    window.settings.sync()
    other_repository = HistoryRepository(
        window.lab.repository.connection.execute("PRAGMA database_list").fetchone()[2]
    )
    try:
        restored = MainWindow(LabSession(other_repository), window.settings)
        qtbot.addWidget(restored)
        restored.show()
        click(qtbot, restored, restored.resume_button)
        assert restored.current_page is restored.consequence
        assert "0 → 30" in restored.consequence.risk_change.text()
        click(qtbot, restored, restored.consequence.continue_button)
        assert restored.lab.node.id == "fake_site"
        assert restored.current_page is restored.situation
        restored.close()
    finally:
        other_repository.close()


def test_failed_save_keeps_situation_and_does_not_show_fake_consequence(qtbot, window, monkeypatch):
    start(qtbot, window)
    before = window.lab.active
    errors = []
    monkeypatch.setattr(QMessageBox, "critical", lambda *args: errors.append(args[-1]))
    window.lab.repository.connection.execute("""
        CREATE TRIGGER reject_save BEFORE UPDATE OF active_entry_id ON sessions
        BEGIN
            SELECT RAISE(ABORT, 'test save failure');
        END
    """)
    button = window.situation.findChild(QPushButton, "choice_report")
    click(qtbot, window, button)
    assert window.current_page is window.situation
    assert window.lab.active == before
    assert len(window.lab.entries) == 1
    assert errors and "test save failure" in errors[0]
    assert not window.settings.value("pending_feedback", "")


@pytest.mark.parametrize("size", [(1280, 720), (1366, 768), (853, 480), (640, 420)])
def test_small_screen_text_wraps_and_controls_remain_reachable(qtbot, window, size):
    window.resize(*size)
    start(qtbot, window)
    # Проверяем реальные размеры виджетов после расчёта раскладки Qt.
    area = window.pages[window.situation]
    qtbot.waitUntil(lambda: area.viewport().width() > 0)
    assert area.widget().width() <= area.viewport().width()
    for button in window.situation.findChildren(QPushButton):
        for label in button.findChildren(QLabel):
            qtbot.waitUntil(
                lambda label=label: label.height() >= label.heightForWidth(label.width())
            )
            assert label.width() <= button.width()
    choose(qtbot, window, "open_link")
    choose(qtbot, window, "submit")
    choose(qtbot, window, "ignore")
    click(qtbot, window, window.results.compare_button)
    area = window.pages[window.comparison]
    qtbot.waitUntil(lambda: area.widget().width() <= area.viewport().width())
    assert window.comparison.overviews[0].risk.isVisible()
    # Длинный разбор целиком доступен вертикальной прокруткой.
    area.ensureWidgetVisible(window.comparison.conclusion)
    qtbot.waitUntil(
        lambda: (
            area.viewport()
            .rect()
            .contains(window.comparison.conclusion.mapTo(area.viewport(), QPoint(0, 0)))
        )
    )
    assert window.comparison.conclusion.height() >= window.comparison.conclusion.heightForWidth(
        window.comparison.conclusion.width()
    )
    assert window.width() == size[0]
    assert window.height() == size[1]


def test_real_entrypoint_starts_event_loop_and_exits_cleanly(tmp_path):
    script = """
import sys
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication
from cyberlab.app import main
QSettings.setDefaultFormat(QSettings.Format.IniFormat)
QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, sys.argv[2])
def finish():
    app = QApplication.instance()
    windows = app.topLevelWidgets()
    valid = any(w.isVisible() and w.windowTitle().startswith('CYBERLAB') for w in windows)
    app.exit(0 if valid else 2)
original = QApplication.exec
def run(app):
    QTimer.singleShot(150, finish)
    return original()
QApplication.exec = run
raise SystemExit(main(['--database', sys.argv[1]]))
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path / "launch.sqlite3"), str(tmp_path / "config")],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    repo = HistoryRepository(tmp_path / "launch.sqlite3")
    try:
        assert len(LabSession(repo).entries) == 1
    finally:
        repo.close()
