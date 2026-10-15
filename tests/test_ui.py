import os
import subprocess
import sys

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QScrollArea

from cyberlab.session import LabSession
from cyberlab.storage import HistoryRepository
from cyberlab.ui import MainWindow


@pytest.fixture
def window(qtbot, tmp_path):
    repo = HistoryRepository(tmp_path / "ui.sqlite3")
    widget = MainWindow(LabSession(repo))
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitUntil(widget.isVisible)
    yield widget
    widget.close()
    repo.close()


def choose(qtbot, window, choice_id):
    button = window.findChild(QPushButton, f"choice_{choice_id}")
    assert button is not None
    window.findChild(QScrollArea).ensureWidgetVisible(button)
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: not button.isVisible())


def test_gui_exercises_attack_rewind_alternative_and_comparison(qtbot, window):
    root_id = window.lab.active.id
    choose(qtbot, window, "open_link")
    assert window.computer.tabs.currentIndex() == 3
    choose(qtbot, window, "submit")
    choose(qtbot, window, "ignore")
    damage_id = window.lab.active.id
    assert "100 / 100" == window.metric_values[0].text()
    assert "Содержимое недоступно" in window.computer.file_content.toPlainText()
    assert window.computer.journal.count() == 4

    # Используем само дерево, а не обход интерфейса через методы модели.
    window.history.setCurrentItem(window.history.topLevelItem(0))
    qtbot.waitUntil(lambda: window.lab.active.id == root_id)
    assert "Учебный бюджет" in window.computer.file_content.toPlainText()
    choose(qtbot, window, "report")
    assert "карантин" in window.computer.mail_status.text().lower()
    assert len(window.lab.entries) == 5
    assert window.left_branch.currentData() == damage_id
    assert window.right_branch.currentData() == window.lab.active.id
    assert window.comparison.item(0, 1).text() == "100 / 100"
    assert window.comparison.item(0, 2).text() == "0 / 100"
    assert window.comparison.item(2, 1).text() == "Зашифрованы"
    assert window.comparison.item(2, 2).text() == "Доступны"
    assert window.history.topLevelItem(0).childCount() == 2
    assert window.comparison_body.isVisible()


def test_inspection_reveals_addresses_and_back_button_preserves_branch(qtbot, window):
    choose(qtbot, window, "inspect")
    assert "help@cyberlab-support.invalid" in window.computer.mail_details.text()
    inspected = window.lab.active
    qtbot.mouseClick(window.restart_button, Qt.MouseButton.LeftButton)
    assert window.lab.active.parent_id is None
    assert not window.lab.active.state.email_inspected
    choose(qtbot, window, "inspect")
    assert window.lab.active == inspected
    assert len(window.lab.entries) == 2


def test_comparison_selectors_do_not_move_active_history(qtbot, window):
    choose(qtbot, window, "open_link")
    choose(qtbot, window, "close_report")
    active = window.lab.active
    window.left_branch.setCurrentIndex(0)
    window.right_branch.setCurrentIndex(1)
    assert window.comparison.item(0, 1).text() == "0 / 100"
    assert window.comparison.item(0, 2).text() == "30 / 100"
    assert window.lab.active == active


def test_comparison_can_collapse_on_small_screens(qtbot, window):
    window.resize(1120, 720)
    assert not window.comparison_body.isVisible()
    choose(qtbot, window, "report")
    assert window.comparison_body.isVisible()
    qtbot.mouseClick(window.comparison_toggle, Qt.MouseButton.LeftButton)
    assert not window.comparison_body.isVisible()
    assert window.lab.node.id == "reported"


def test_gui_restart_shows_saved_state(qtbot, tmp_path):
    path = tmp_path / "restart.sqlite3"
    repo = HistoryRepository(path)
    lab = LabSession(repo)
    lab.choose("open_link")
    lab.choose("submit")
    lab.choose("isolate")
    repo.close()
    repo = HistoryRepository(path)
    try:
        widget = MainWindow(LabSession(repo))
        qtbot.addWidget(widget)
        widget.show()
        assert "Ущерб ограничен" in widget.story_title.text()
        assert widget.metric_values[3].text() == "Отключена"
        assert widget.computer.journal.count() == 4
        assert len(widget.lab.entries) == 4
        widget.close()
    finally:
        repo.close()


def test_real_entrypoint_starts_event_loop_and_exits_cleanly(tmp_path):
    # Запускаем app.main в отдельном процессе с настоящим циклом Qt. Таймер лишь
    # завершает smoke test; в приложении нет специального тестового режима.
    script = """
import sys
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from cyberlab.app import main
def finish():
    app = QApplication.instance()
    windows = app.topLevelWidgets()
    assert any(w.isVisible() and w.windowTitle().startswith('CYBERLAB') for w in windows)
    app.quit()
original = QApplication.exec
def run(app):
    QTimer.singleShot(150, finish)
    return original()
QApplication.exec = run
raise SystemExit(main(['--database', sys.argv[1]]))
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path / "launch.sqlite3")],
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
