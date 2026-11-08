"""Кроссплатформенная точка входа. Qt выбирает каталог данных пользователя."""

import argparse
import sqlite3
import sys
from pathlib import Path

from PySide6.QtCore import QLibraryInfo, QLocale, QStandardPaths, QTranslator
from PySide6.QtWidgets import QApplication

from cyberlab.desktop import application_icon, integrate_appimage
from cyberlab.session import LabSession
from cyberlab.storage import HistoryRepository
from cyberlab.ui import MainWindow
from cyberlab.ui_helpers import show_error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CYBERLAB — локальная лаборатория киберугроз")
    parser.add_argument(
        "--database", type=Path, help="Путь к SQLite; по умолчанию — каталог данных пользователя"
    )
    parser.add_argument("--smoke-test", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    app = QApplication([sys.argv[0]])
    QLocale.setDefault(QLocale(QLocale.Language.Russian))
    # Переводит и стандартные меню Qt (копирование, выделение), а не только наши подписи.
    translator = QTranslator(app)
    translator.load("qtbase_ru", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))
    app.installTranslator(translator)
    app.setApplicationName("CYBERLAB")
    app.setOrganizationName("CYBERLAB")
    app.setDesktopFileName("cyberlab")
    app.setWindowIcon(application_icon())
    if args.smoke_test:
        from cyberlab.diagnostics import run_smoke_test

        return run_smoke_test(app, args.smoke_test)
    integrate_appimage()
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
        show_error(None, "CYBERLAB: не удалось открыть историю", error)
        return 1
    app.aboutToQuit.connect(repository.close)
    window.show()
    return app.exec()
