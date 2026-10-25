"""Проверить реальный цикл Qt, ветки и SQLite при запрете сетевых операций Python."""

import sys
import traceback
from pathlib import Path
from tempfile import TemporaryDirectory

network_attempts = []


def reject_network(event: str, arguments: tuple) -> None:
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto", "socket.bind"}:
        network_attempts.append(event)
        raise RuntimeError(f"Приложение пыталось использовать сеть: {event}")


# Хук устанавливается до импорта приложения: охватывает также его запуск.
# Нативные библиотеки Qt не покрываются Python audit hook; это не сетевой namespace.
sys.addaudithook(reject_network)

from PySide6.QtCore import QSettings, QTimer  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QPushButton  # noqa: E402

import cyberlab  # noqa: E402
from cyberlab.session import LabSession  # noqa: E402
from cyberlab.storage import HistoryRepository  # noqa: E402
from cyberlab.ui import MainWindow  # noqa: E402


def main() -> int:
    if "--installed" in sys.argv:
        # Проверяем именно пакет в новом venv, а не editable-копию из checkout.
        assert Path(cyberlab.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
    app = QApplication([])
    with TemporaryDirectory(prefix="cyberlab-offline-") as directory:
        folder = Path(directory)
        marker = folder / "Настоящий файл.txt"
        marker.write_text("Настоящие файлы не меняются", encoding="utf-8")
        database = folder / "Учебная история.sqlite3"
        settings = QSettings(str(folder / "settings.ini"), QSettings.Format.IniFormat)
        settings.setValue("tutorial_completed", True)
        repository = HistoryRepository(database)
        window = MainWindow(LabSession(repository), settings)
        window.show()

        def run_checks() -> None:
            try:
                window.start_button.click()
                for choice in ("open_link", "submit", "ignore"):
                    window.situation.findChild(QPushButton, f"choice_{choice}").click()
                    QTest.qWait(20)
                    assert window.current_page is window.consequence
                    window.consequence.continue_button.click()
                damage = window.lab.active
                assert damage.state.files_encrypted and damage.state.risk == 100
                window.results.change_button.click()
                window.decisions.root_button.click()
                assert not window.lab.active.state.files_encrypted
                window.situation.findChild(QPushButton, "choice_report").click()
                window.consequence.continue_button.click()
                safe = window.lab.active
                assert safe.state.risk == 0 and not safe.state.credentials_exposed
                window.results.compare_button.click()
                selected = {combo.currentData() for combo in window.comparison.selectors}
                assert selected == {damage.id, safe.id}
                original_entries = window.lab.entries
                assert len(original_entries) == 5
                window.close()
                repository.close()
                restored_repository = HistoryRepository(database)
                try:
                    restored = LabSession(restored_repository)
                    assert restored.active == safe
                    assert restored.entries == original_entries
                    assert (
                        restored_repository.connection.execute("PRAGMA integrity_check").fetchone()[
                            0
                        ]
                        == "ok"
                    )
                finally:
                    restored_repository.close()
                assert marker.read_text(encoding="utf-8") == "Настоящие файлы не меняются"
                assert not network_attempts, network_attempts
                print("Offline smoke passed: Qt, attack, rewind, safe branch, comparison, SQLite.")
                app.exit(0)
            except Exception:
                traceback.print_exc()
                app.exit(1)

        QTimer.singleShot(0, run_checks)
        result = app.exec()
        # При ошибке также закрываем окно и БД, особенно важно для Windows.
        window.close()
        repository.close()
        return result


if __name__ == "__main__":
    raise SystemExit(main())
