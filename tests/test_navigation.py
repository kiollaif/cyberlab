"""Переходы нового рабочего пространства должны сохранять учебный снимок и контекст."""

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QPushButton

from cyberlab.session import LabSession
from cyberlab.storage import HistoryRepository
from cyberlab.ui import MainWindow


@pytest.fixture
def workspace(qtbot, tmp_path):
    repository = HistoryRepository(tmp_path / "navigation.sqlite3")
    settings = QSettings(str(tmp_path / "preferences.ini"), QSettings.Format.IniFormat)
    settings.setValue("tutorial_completed", True)
    window = MainWindow(LabSession(repository), settings)
    qtbot.addWidget(window)
    window.resize(1366, 768)
    window.show()
    qtbot.waitUntil(window.isVisible)
    yield window
    window.close()
    repository.close()


def test_sidebar_preserves_unread_consequence_and_all_snapshots(qtbot, workspace):
    window = workspace
    window.start_button.click()
    window.situation.findChild(QPushButton, "choice_open_link").click()
    before = window.lab.entries
    active = window.lab.active
    for section, page in (
        ("computer", window.computer),
        ("decisions", window.decisions),
        ("comparison", window.comparison),
        ("mentor", window.ai_mentor),
        ("sessions", window.saved_sessions),
        ("simulation", window.consequence),
    ):
        qtbot.mouseClick(window.navigation.buttons[section], Qt.MouseButton.LeftButton)
        assert window.current_page is page
        assert window.navigation.buttons[section].isChecked()
        assert sum(button.isChecked() for button in window.navigation.buttons.values()) == 1
        assert window.lab.active == active
        assert window.lab.entries == before
        assert not window.ai_mentor.busy
    window.consequence.continue_button.click()
    assert window.current_page is window.situation
    assert window.lab.active == active


def test_overview_only_offers_primary_start_and_optional_resume(workspace):
    window = workspace
    assert window.menu.findChildren(QPushButton) == [window.start_button, window.resume_button]
    assert not window.resume_button.isVisible()
    assert window.start_button.isVisible()
    assert window.start_button.width() < window.pages[window.menu].viewport().width() / 2
    assert window.start_button.height() <= 40


@pytest.mark.parametrize("size", [(1366, 768), (640, 420)])
def test_sidebar_and_all_sections_fit_the_viewport(qtbot, workspace, size):
    window = workspace
    window.resize(*size)
    qtbot.waitUntil(lambda: window.navigation.compact == (window.width() < 980))
    for name in (
        "home",
        "simulation",
        "decisions",
        "comparison",
        "sessions",
        "computer",
        "mentor",
        "help",
    ):
        button = window.navigation.buttons[name]
        assert button.toolTip() == window.navigation.titles[name]
        assert not button.icon().isNull()
        qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
        page = window.current_page
        area = window.pages[page]
        qtbot.waitUntil(lambda area=area: area.widget().width() <= area.viewport().width())
        assert page.isVisible()
    assert window.navigation.width() == (60 if window.width() < 980 else 202)
