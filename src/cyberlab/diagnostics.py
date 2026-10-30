"""Проверка готового исполняемого файла в CI без Python на целевой системе.

Запускается только скрытым флагом --smoke-test. Работает с временной БД,
не затрагивает историю ученика и запрещает сетевые операции Python.
"""

import json
import os
import platform
import sys
import traceback
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtCore import QCoreApplication, QSettings, QStandardPaths, QTimer, qVersion
from PySide6.QtWidgets import QApplication, QPushButton

from cyberlab import __version__
from cyberlab.desktop import application_icon, integrate_appimage
from cyberlab.reports import build_report
from cyberlab.scenarios import SCENARIOS
from cyberlab.session import LabSession
from cyberlab.storage import HistoryRepository
from cyberlab.ui import MainWindow


def run_smoke_test(app: QApplication, report_path: Path) -> int:
    os.environ.pop("DEEPSEEK_API_KEY", None)
    os.environ["CYBERLAB_AI_PROVIDER"] = "local"
    network_attempts = []

    def reject_network(event, arguments):
        if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto", "socket.bind"}:
            network_attempts.append(event)
            raise RuntimeError(f"Сетевой запрос во время офлайн-проверки: {event}")

    sys.addaudithook(reject_network)
    report = {
        "success": False,
        "version": __version__,
        "os": platform.platform(),
        "qt": qVersion(),
        "qt_platform": app.platformName(),
        "desktop": os.environ.get("XDG_CURRENT_DESKTOP", ""),
        "frozen": bool(getattr(sys, "frozen", False)),
        "data_directory": QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppLocalDataLocation
        ),
        "checks": [],
    }
    with TemporaryDirectory(prefix="cyberlab-smoke-") as directory:
        folder = Path(directory)
        database = folder / "История.sqlite3"
        settings = QSettings(str(folder / "settings.ini"), QSettings.Format.IniFormat)
        settings.setValue("tutorial_completed", True)
        repository = HistoryRepository(database)
        window = MainWindow(LabSession(repository), settings)
        window.show()

        def check() -> None:
            try:
                assert window.isVisible() and not application_icon().isNull()
                assert "Копир" in QCoreApplication.translate("QWidgetTextControl", "&Copy")
                report["checks"].append("window, bundled icon, Russian Qt translation")
                window.start_button.click()
                window.training_start_button.click()
                for choice in ("open_link", "submit", "ignore"):
                    window.situation.findChild(QPushButton, f"choice_{choice}").click()
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
                assert {combo.currentData() for combo in window.comparison.selectors} == {
                    damage.id,
                    safe.id,
                }
                entries = window.lab.entries
                report["checks"].append("attack, rewind, safe alternative, branch comparison")
                # Нет ключа и сети: локальный наставник должен реально вернуть ответ.
                window.navigation.buttons["mentor"].click()
                window.ai_mentor.question.setPlainText("Как распознать фишинг?")
                window.ai_mentor.ask_button.click()
                # Локальный ответ также проходит через QThread: проверим его позже.
                QTimer.singleShot(100, lambda: finish(safe, entries))
            except Exception:
                fail()

        def finish(safe, entries) -> None:
            try:
                if window.ai_mentor.worker is not None:
                    QTimer.singleShot(50, lambda: finish(safe, entries))
                    return
                assert window.ai_mentor.answer.toPlainText().strip()
                assert "офлайн" in window.ai_mentor.mode.text()
                assert window.lab.active == safe and window.lab.entries == entries
                scenario_results = {}
                for scenario in SCENARIOS[1:]:
                    window.show_menu()
                    window.scenario_selector.setCurrentIndex(
                        window.scenario_selector.findData(scenario.id)
                    )
                    window.start_button.click()
                    window.training_start_button.click()
                    root = window.lab.active.id
                    while not window.lab.node.terminal:
                        preferred = (
                            "open_attachment",
                            "open_link",
                            "connect",
                            "enable_macros",
                            "submit",
                            "run",
                        )
                        choice = next(
                            (c for c in window.lab.node.choices if c.id in preferred),
                            window.lab.node.choices[-1],
                        )
                        window.situation.findChild(QPushButton, f"choice_{choice.id}").click()
                        assert window.current_page is window.consequence
                        window.consequence.continue_button.click()
                    dangerous = window.lab.active
                    assert dangerous.state.risk >= 90
                    window._go_to(root)
                    safe_choice = {
                        "attachment": "quarantine",
                        "website": "bookmark",
                        "usb": "hand_over",
                    }[scenario.kind]
                    window.situation.findChild(QPushButton, f"choice_{safe_choice}").click()
                    window.consequence.continue_button.click()
                    safer = window.lab.active
                    assert safer.state.risk == 0 and not safer.state.files_encrypted
                    window.results.compare_button.click()
                    assert {c.currentData() for c in window.comparison.selectors} == {
                        dangerous.id,
                        safer.id,
                    }
                    text = build_report(scenario, window.lab.entries, safer)
                    export = folder / "Отчёт.txt"
                    export.write_text(text, encoding="utf-8")
                    assert export.read_text(encoding="utf-8") == text
                    assert scenario.title in text and dangerous.choice_title not in text
                    scenario_results[scenario.id] = safer
                report["checks"].append("four scenarios, rewind, alternatives, TXT report")
                window.close()
                repository.close()
                restored = HistoryRepository(database)
                try:
                    lab = LabSession(restored)
                    assert lab.active == safe and lab.entries == entries
                    for scenario in SCENARIOS[1:]:
                        lab.switch_scenario(scenario)
                        assert lab.active == scenario_results[scenario.id]
                    assert (
                        restored.connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                    )
                finally:
                    restored.close()
                if os.environ.get("APPIMAGE"):
                    assert integrate_appimage()
                    report["checks"].append("AppImage menu integration")
                assert not network_attempts, network_attempts
                report["checks"].extend(
                    ["local mentor, unchanged simulation", "SQLite reopen, offline"]
                )
                report["success"] = True
                app.exit(0)
            except Exception:
                fail()

        def fail() -> None:
            report["error"] = traceback.format_exc()
            app.exit(1)

        QTimer.singleShot(0, check)
        # Ошибка фонового потока не должна навсегда зависнуть в сборочном задании.
        QTimer.singleShot(30000, lambda: (report.update(error="Smoke test timed out"), app.exit(1)))
        result = app.exec()
        window.close()
        repository.close()
    report["network_attempts"] = network_attempts
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
