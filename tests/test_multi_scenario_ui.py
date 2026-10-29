"""Выбор сценария, последствия, возврат и экспорт через настоящий UI Qt."""

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QFileDialog, QPushButton

from cyberlab.scenarios import SCENARIOS
from cyberlab.session import LabSession
from cyberlab.storage import HistoryRepository
from cyberlab.ui import MainWindow


@pytest.fixture
def multi_window(qtbot, tmp_path):
    repository = HistoryRepository(tmp_path / "history.sqlite3")
    settings = QSettings(str(tmp_path / "prefs.ini"), QSettings.Format.IniFormat)
    settings.setValue("tutorial_completed", True)
    window = MainWindow(LabSession(repository), settings)
    qtbot.addWidget(window)
    window.show()
    yield window
    window.close()
    repository.close()


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_select_play_rewind_compare_and_export(
    qtbot, multi_window, scenario, tmp_path, monkeypatch
):
    window = multi_window
    window.scenario_selector.setCurrentIndex(window.scenario_selector.findData(scenario.id))
    window.start_button.click()
    root = window.lab.active.id
    while not window.lab.node.terminal:
        # Выбираем ветку запуска, если она доступна; в остальных узлах — последний выбор.
        choices = window.lab.node.choices
        choice = next(
            (
                c
                for c in choices
                if c.id
                in ("open_link", "open_attachment", "connect", "enable_macros", "submit", "run")
            ),
            choices[-1],
        )
        window.situation.findChild(QPushButton, "choice_" + choice.id).click()
        assert window.current_page is window.consequence
        assert window.consequence.reason.text()
        window.consequence.continue_button.click()
    assert window.current_page is window.results
    old_entries = window.lab.entries
    assert window.results.risk_history.text()
    destination = tmp_path / "Учебный отчёт.txt"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *a, **k: (str(destination), "Текст UTF-8 (*.txt)")
    )
    window.results.export_button.click()
    assert scenario.title in destination.read_text(encoding="utf-8")
    assert "Отчёт сохранён" in window.results.export_status.text()
    window._go_to(root)
    window.results.compare_button.click()
    assert window.current_page is window.comparison
    assert window.lab.entries == old_entries
    assert window.lab.active.id == root
    window._open_computer()
    assert scenario.mail_subject == window.computer.source_title.text()
    if scenario.kind == "usb":
        assert window.computer.tabs.tabText(0) == "Источник"
        assert "письм" not in window.computer.mentor_state.text().lower()


def test_switching_keeps_unread_feedback_and_restores_scenario(qtbot, multi_window):
    window = multi_window
    window.start_button.click()
    window.situation.findChild(QPushButton, "choice_open_link").click()
    original = window.lab.active
    window.show_menu()
    window.scenario_selector.setCurrentIndex(3)
    window.start_button.click()
    window.situation.findChild(QPushButton, "choice_connect").click()
    window.consequence.continue_button.click()
    window.show_menu()
    window.scenario_selector.setCurrentIndex(0)
    window._resume()
    assert window.current_page is window.consequence
    assert window.lab.active == original
    window.show_menu()
    window.scenario_selector.setCurrentIndex(3)
    restored = MainWindow(LabSession(window.lab.repository), window.settings)
    qtbot.addWidget(restored)
    assert restored.lab.scenario.id == "usb-v1"
    assert restored.lab.active.node_id == "connected"
    restored.close()
