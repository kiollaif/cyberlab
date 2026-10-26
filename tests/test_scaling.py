"""Отдельный процесс нужен, потому что Qt читает масштаб при создании QApplication."""

import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    ("scale", "width", "height"),
    [
        ("1", 1280, 720),
        ("1", 1366, 768),
        ("1", 853, 480),
        ("1", 640, 420),
        ("1.25", 1024, 576),
        ("1.5", 853, 480),
    ],
)
def test_qt_scaling_keeps_russian_text_and_navigation_available(tmp_path, scale, width, height):
    script = """
import sys
from time import monotonic
from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton
from cyberlab.session import LabSession
from cyberlab.storage import HistoryRepository
from cyberlab.ui import MainWindow
def wait_until(predicate, message):
    deadline = monotonic() + 5
    while True:
        QTest.qWait(10)
        if predicate():
            return
        assert monotonic() < deadline, (
            message, window.size().toTuple(),
            [(combo.width(), combo.minimumSizeHint().width())
             for combo in window.comparison.selectors],
            window.comparison.include_steps.minimumSizeHint().width(),
            window.pages[window.comparison].viewport().width(),
        )
app = QApplication([])
settings = QSettings(sys.argv[1], QSettings.Format.IniFormat)
settings.setValue('tutorial_completed', True)
repository = HistoryRepository(':memory:')
window = MainWindow(LabSession(repository), settings)
scale = float(sys.argv[2])
width, height = int(sys.argv[4]), int(sys.argv[5])
window.resize(width, height)
window.show()
app.processEvents()
assert abs(window.devicePixelRatioF() - scale) < 0.01
assert (window.width(), window.height()) == (width, height)
window.start_button.click()
for choice in ('open_link', 'submit', 'ignore'):
    # Qt пересчитывает вложенные раскладки через очередь событий после показа.
    area = window.pages[window.current_page]
    wait_until(lambda: area.widget().width() <= area.viewport().width(), 'Situation width')
    for button in window.situation.findChildren(QPushButton):
        if button.text():
            wait_until(lambda: button.width() >= button.minimumSizeHint().width(), button.text())
            wait_until(lambda: button.height() >= button.minimumSizeHint().height(), button.text())
        for label in button.findChildren(QLabel):
            wait_until(lambda: label.height() >= label.heightForWidth(label.width()), label.text())
    window.situation.findChild(QPushButton, 'choice_' + choice).click()
    app.processEvents()
    assert window.current_page is window.consequence
    window.consequence.continue_button.click()
assert window.current_page is window.results
window.results.compare_button.click()
window.comparison.details_toggle.click()
area = window.pages[window.comparison]
wait_until(lambda: area.widget().width() <= area.viewport().width(), 'Comparison width')
for label in window.comparison.findChildren(QLabel):
    if label.isVisible():
        wait_until(lambda: label.height() >= label.heightForWidth(label.width()), label.text())
window.grab().save(sys.argv[3])
assert (window.width(), window.height()) == (width, height)
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
            str(width),
            str(height),
        ],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "QT_SCALE_FACTOR": scale},
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
