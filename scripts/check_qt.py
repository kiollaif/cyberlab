"""Проверить предпосылки Qt до pytest, чтобы не потерять причину SIGABRT в CI."""

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QLibraryInfo


def main() -> None:
    platform = os.environ.get("QT_QPA_PLATFORM", "")
    if sys.platform.startswith("linux") and platform == "xcb":
        plugin_directory = QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)
        plugin = Path(plugin_directory) / "platforms" / "libqxcb.so"
        result = subprocess.run(["ldd", str(plugin)], capture_output=True, text=True, check=True)
        missing = [line.strip() for line in result.stdout.splitlines() if "not found" in line]
        if missing:
            raise RuntimeError("Не хватает библиотек XCB:\n" + "\n".join(missing))
        if not os.environ.get("DISPLAY"):
            raise RuntimeError("Для xcb нужен DISPLAY. Запустите проверку через xvfb-run.")

    # Нативный плагин может завершить процесс через abort. Отдельный процесс
    # оставляет сообщение Qt в журнале и не обрывает весь сбор тестов pytest.
    probe = """
import os, platform
from PySide6.QtCore import qVersion
from PySide6.QtWidgets import QApplication
app = QApplication([])
expected = os.environ.get('QT_QPA_PLATFORM')
assert not expected or app.platformName() == expected
print('OS:', platform.platform())
print('Qt:', qVersion(), 'platform:', app.platformName())
print('Available desktop:', app.primaryScreen().availableGeometry().getRect())
"""
    result = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True)
    print(result.stdout, end="")
    if result.returncode:
        raise RuntimeError(f"Qt probe exited with {result.returncode}:\n{result.stderr}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        if os.environ.get("GITHUB_ACTIONS"):
            # Аннотация доступна на странице задания даже без скачивания логов.
            message = str(error).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
            print(f"::error title=Qt startup::{message}")
        raise
