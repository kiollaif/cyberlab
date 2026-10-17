"""Отдельный процесс нужен, потому что Qt читает масштаб при создании QApplication."""

import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize("scale", ["1.25", "1.5"])
def test_qt_scaling_keeps_russian_text_and_navigation_available(tmp_path, scale):
    script = """
import sys
from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton
from cyberlab.session import LabSession
from cyberlab.storage import HistoryRepository
from cyberlab.ui import MainWindow
app = QApplication([])
settings = QSettings(sys.argv[1], QSettings.Format.IniFormat)
settings.setValue('tutorial_completed', True)
repository = HistoryRepository(':memory:')
window = MainWindow(LabSession(repository), settings)
scale = float(sys.argv[2])
window.resize(round(1280 / scale), round(720 / scale))
window.show()
app.processEvents()
assert abs(window.devicePixelRatioF() - scale) < 0.01
window.start_button.click()
for choice in ('open_link', 'submit', 'ignore'):
    # Qt пересчитывает вложенные раскладки через очередь событий после показа.
    QTest.qWait(50)
    area = window.pages[window.current_page]
    assert area.widget().width() <= area.viewport().width()
    for button in window.situation.findChildren(QPushButton):
        for label in button.findChildren(QLabel):
            assert label.height() >= label.heightForWidth(label.width()), label.text()
    window.situation.findChild(QPushButton, 'choice_' + choice).click()
    app.processEvents()
    assert window.current_page is window.consequence
    window.consequence.continue_button.click()
assert window.current_page is window.results
window.results.compare_button.click()
window.comparison.details_toggle.click()
QTest.qWait(50)
area = window.pages[window.comparison]
assert area.widget().width() <= area.viewport().width()
for label in window.comparison.findChildren(QLabel):
    if label.isVisible():
        assert label.height() >= label.heightForWidth(label.width()), label.text()
window.grab().save(sys.argv[3])
window.close()
repository.close()
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(tmp_path / "settings.ini"),
            scale,
            str(tmp_path / "scaled.png"),
        ],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "QT_SCALE_FACTOR": scale},
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
