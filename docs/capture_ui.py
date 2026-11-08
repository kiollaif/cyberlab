"""Получить настоящие снимки интерфейса с временной учебной историей.

Для Linux без дисплея: QT_QPA_PLATFORM=offscreen uv run python docs/capture_ui.py.
Никакие пользовательские базы, ключи и онлайн-запросы не используются.
"""

import argparse
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton

from cyberlab.pdf_report import build_pdf_report
from cyberlab.session import LabSession
from cyberlab.storage import HistoryRepository
from cyberlab.ui import MainWindow


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("docs/v2"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    os.environ["CYBERLAB_AI_PROVIDER"] = "local"
    app = QApplication([])
    with TemporaryDirectory(prefix="cyberlab-capture-") as folder:
        repository = HistoryRepository(Path(folder) / "history.sqlite3")
        settings = QSettings(folder + "/settings.ini", QSettings.Format.IniFormat)
        window = MainWindow(LabSession(repository), settings)
        window.resize(1366, 768)
        window.show()

        def click(button) -> None:
            area = window.pages[window.current_page]
            if area.isAncestorOf(button):
                area.ensureWidgetVisible(button)
            QTest.qWait(30)
            QTest.mouseClick(button, Qt.MouseButton.LeftButton)
            QTest.qWait(30)

        def capture(name) -> None:
            QTest.qWait(100)
            target = args.output / (name + ".png")
            if not window.grab().save(str(target)):
                raise OSError("Не удалось сохранить " + str(target))

        try:
            capture("home")
            click(window.help_button)
            capture("lesson")
            for step in range(5):
                if step == 2:
                    click(window.tutorial.practice_button)
                if step < 4:
                    click(window.tutorial.next_button)
            click(window.tutorial.finish_button)
            click(window.start_button)
            capture("catalog")
            click(window.training_start_button)
            capture("situation")
            for action in ("open_link", "submit", "ignore"):
                click(window.situation.findChild(QPushButton, "choice_" + action))
                if action == "open_link":
                    capture("consequence")
                click(window.consequence.continue_button)
            capture("result")
            (args.output / "example-report.pdf").write_bytes(
                build_pdf_report(window.lab.scenario, window.lab.entries, window.lab.active)
            )
            click(window.results.change_button)
            click(window.decisions.root_button)
            click(window.situation.findChild(QPushButton, "choice_report"))
            click(window.consequence.continue_button)
            window.show_menu()
            click(window.sessions_button)
            capture("history")
            window._open_ai()
            capture("helper")
            print("Captured eight screens, a branched history and a PDF in", args.output)
        finally:
            window.close()
            app.processEvents()
            repository.close()


if __name__ == "__main__":
    main()
