"""Иконка и регистрация AppImage в пользовательском меню Linux."""

import os
from pathlib import Path

from PySide6.QtCore import QStandardPaths
from PySide6.QtGui import QIcon


def application_icon() -> QIcon:
    # PyInstaller сохраняет ресурсы рядом с модулем, как и установленный wheel.
    return QIcon(str(Path(__file__).parent / "resources" / "cyberlab.png"))


def desktop_command(path: Path) -> str:
    """Заключить путь в кавычки по правилам Exec в .desktop, а не shell."""
    value = str(path)
    if "\n" in value or "\r" in value:
        raise ValueError("Путь приложения содержит перевод строки")
    # Процент — код подстановки desktop entry; обратная косая проходит два разбора.
    value = value.replace("\\", "\\\\\\\\").replace("%", "%%")
    for character in ('"', "`", "$"):
        value = value.replace(character, "\\\\" + character)
    return f'"{value}"'


def integrate_appimage() -> bool:
    """После запуска AppImage добавить ярлык и иконку, не требуя прав root."""
    image = os.environ.get("APPIMAGE")
    if not image:
        return False
    executable = Path(image)
    if not executable.is_absolute() or not executable.is_file():
        return False
    applications = Path(
        QStandardPaths.writableLocation(QStandardPaths.StandardLocation.ApplicationsLocation)
    )
    data = Path(
        QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericDataLocation)
    )
    icon = data / "icons" / "hicolor" / "256x256" / "apps" / "cyberlab.png"
    try:
        applications.mkdir(parents=True, exist_ok=True)
        icon.parent.mkdir(parents=True, exist_ok=True)
        icon.write_bytes((Path(__file__).parent / "resources" / "cyberlab.png").read_bytes())
        entry = (
            "[Desktop Entry]\nType=Application\nName=CYBERLAB\n"
            "Comment=Учебная лаборатория кибербезопасности\n"
            f"Exec=/usr/bin/env {desktop_command(executable)}\nIcon=cyberlab\nTerminal=false\n"
            "Categories=Education;Security;\nStartupWMClass=CYBERLAB\n"
        )
        (applications / "cyberlab.desktop").write_text(entry, encoding="utf-8")
    except (OSError, ValueError):
        # Недоступное меню не должно мешать запуску и работе с историей.
        return False
    return True
