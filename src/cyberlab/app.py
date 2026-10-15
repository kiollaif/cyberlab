"""Кроссплатформенная точка входа. Qt выбирает каталог данных пользователя."""

import argparse
import sqlite3
import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QApplication, QMessageBox

from cyberlab.session import LabSession
from cyberlab.storage import HistoryRepository
from cyberlab.ui import MainWindow


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CYBERLAB — локальная лаборатория киберугроз")
    parser.add_argument(
        "--database", type=Path, help="Путь к SQLite; по умолчанию — каталог данных пользователя"
    )
    args = parser.parse_args(argv)
    app = QApplication([sys.argv[0]])
    app.setApplicationName("CYBERLAB")
    app.setOrganizationName("CYBERLAB")
    directory = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppLocalDataLocation
    )
    database = args.database or Path(directory) / "cyberlab.sqlite3"
    repository = None
    try:
        repository = HistoryRepository(database)
        window = MainWindow(LabSession(repository))
    except (sqlite3.Error, ValueError, OSError, KeyError, TypeError) as error:
        if repository is not None:
            repository.close()
        QMessageBox.critical(
            None, "CYBERLAB: ошибка запуска", f"Не удалось открыть историю.\n{error}"
        )
        return 1
    app.aboutToQuit.connect(repository.close)
    window.show()
    return app.exec()
