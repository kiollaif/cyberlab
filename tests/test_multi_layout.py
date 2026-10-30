"""Четыре сценария на небольших экранах и при масштабе 125/150%."""

import os
import subprocess
import sys

import pytest

SCRIPT = """
import sys
from time import monotonic
from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton
from cyberlab.scenarios import SCENARIOS
from cyberlab.session import LabSession
from cyberlab.storage import HistoryRepository
from cyberlab.ui import MainWindow
app=QApplication([])
repository=HistoryRepository(':memory:')
settings=QSettings(sys.argv[1],QSettings.Format.IniFormat)
settings.setValue('tutorial_completed',True)
window=MainWindow(LabSession(repository),settings)
window.resize(int(sys.argv[2]),int(sys.argv[3])); window.show()
def check():
    deadline=monotonic()+5
    while True:
        QTest.qWait(15)
        area=window.pages[window.current_page]
        buttons=window.current_page.findChildren(QPushButton)
        valid=area.widget().width() <= area.viewport().width()
        for label in window.current_page.findChildren(QLabel):
            if label.isVisible() and label.wordWrap():
                valid=valid and label.height()>=label.heightForWidth(label.width())
        for button in buttons:
            if button.isVisible() and button.text():
                valid=valid and button.width()>=button.minimumSizeHint().width()
                valid=valid and button.height()>=button.minimumSizeHint().height()
            for label in button.findChildren(QLabel):
                if label.isVisible():
                    valid=valid and label.height()>=label.heightForWidth(label.width())
        if valid:return
        assert monotonic()<deadline, (
            window.lab.scenario.id,window.current_page,window.size().toTuple())
for scenario in SCENARIOS:
    window.show_menu()
    check()
    window.start_button.click()
    window.scenario_selector.setCurrentIndex(window.scenario_selector.findData(scenario.id))
    check()
    window.training_start_button.click()
    while not window.lab.node.terminal:
        check()
        choices=window.lab.node.choices
        preferred=('open_link','open_attachment','connect','enable_macros','submit','run')
        choice=next((c for c in choices if c.id in preferred),choices[-1])
        window.situation.findChild(QPushButton,'choice_'+choice.id).click(); check()
        window.consequence.continue_button.click()
    check()
    window.results.details_toggle.click(); check()
    window.results.compare_button.click(); check()
    window.navigation.buttons['mentor'].click(); check()
window.grab().save(sys.argv[4])
window.close(); repository.close()
"""


@pytest.mark.parametrize(
    "scale,width,height",
    [
        ("1", 1280, 720),
        ("1", 1366, 768),
        ("1.25", 1024, 576),
        ("1.5", 910, 512),
    ],
)
def test_each_scenario_layout(tmp_path, scale, width, height):
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            SCRIPT,
            str(tmp_path / "prefs.ini"),
            str(width),
            str(height),
            str(tmp_path / "mentor.png"),
        ],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "QT_SCALE_FACTOR": scale},
        capture_output=True,
        text=True,
        timeout=45,
    )
    assert result.returncode == 0, result.stdout + result.stderr
