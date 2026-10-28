"""Регистрация AppImage не требует root и не трогает SQLite."""

import subprocess
import sys

import pytest
from PySide6.QtCore import QStandardPaths

from cyberlab.desktop import application_icon, integrate_appimage


def test_icon_is_bundled(qapp):
    assert not application_icon().isNull()


def test_regular_launch_does_not_register_appimage(monkeypatch):
    monkeypatch.delenv("APPIMAGE", raising=False)
    assert not integrate_appimage()


def test_appimage_registers_without_changing_user_history(qapp, monkeypatch, tmp_path):
    data = tmp_path / "data"
    applications = data / "applications"
    database = data / "CYBERLAB" / "CYBERLAB" / "cyberlab.sqlite3"
    database.parent.mkdir(parents=True)
    database.write_bytes(b"existing history marker")
    image = tmp_path / "CyberLab portable.AppImage"
    image.touch()
    monkeypatch.setenv("APPIMAGE", str(image))
    monkeypatch.setattr(
        QStandardPaths,
        "writableLocation",
        lambda location: str(
            applications if location == QStandardPaths.ApplicationsLocation else data
        ),
    )
    assert integrate_appimage()
    entry = (applications / "cyberlab.desktop").read_text(encoding="utf-8")
    assert image.name in entry and "Exec=/usr/bin/env" in entry
    assert "Terminal=false" in entry
    assert (data / "icons/hicolor/256x256/apps/cyberlab.png").is_file()
    assert database.read_bytes() == b"existing history marker"
    # Если AppImage переместили, следующий запуск обновляет путь в меню.
    moved = tmp_path / "Moved.AppImage"
    image.rename(moved)
    monkeypatch.setenv("APPIMAGE", str(moved))
    assert integrate_appimage()
    updated = (applications / "cyberlab.desktop").read_text(encoding="utf-8")
    assert moved.name in updated and image.name not in updated


def test_readonly_menu_does_not_prevent_launch(qapp, monkeypatch, tmp_path):
    image = tmp_path / "CyberLab.AppImage"
    image.touch()
    blocker = tmp_path / "not-a-directory"
    blocker.touch()
    monkeypatch.setenv("APPIMAGE", str(image))
    monkeypatch.setattr(QStandardPaths, "writableLocation", lambda _: str(blocker))
    assert not integrate_appimage()


@pytest.mark.skipif(sys.platform != "linux", reason="Linux desktop entry")
def test_desktop_entry_launches_paths_with_reserved_characters(qapp, monkeypatch, tmp_path):
    # Настоящий разбор .desktop через GLib: путь с пробелами и метасимволами
    # обязан запустить нужный файл с нулём аргументов, а не команду оболочки.
    from cyberlab.desktop import desktop_command

    executable = tmp_path / 'Cyber Lab %f $HOME `id` "quoted" \\ test'
    output = tmp_path / "launched.txt"
    executable.write_text(f"#!/bin/sh\nprintf '%s' \"$#\" > '{output}'\n", encoding="utf-8")
    executable.chmod(0o755)
    entry = tmp_path / "test.desktop"
    entry.write_text(
        "[Desktop Entry]\nType=Application\nName=Test\n"
        f"Exec=/usr/bin/env {desktop_command(executable)}\n",
        encoding="utf-8",
    )
    subprocess.run(["desktop-file-validate", str(entry)], check=True, capture_output=True)
    subprocess.run(["gio", "launch", str(entry)], check=True, capture_output=True)
    # GLib запускает приложение асинхронно, ждём ограниченное время.
    import time

    deadline = time.monotonic() + 5
    while not output.exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert output.read_text() == "0"
