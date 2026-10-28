# -*- mode: python ; coding: utf-8 -*-
"""Windows: один EXE. Linux: каталог для AppImage и RPM. Собирать на целевой ОС."""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

root = Path(SPECPATH).parent
windows = sys.platform == "win32"

analysis = Analysis(
    [str(root / "packaging" / "launcher.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=collect_data_files("cyberlab", includes=["resources/*"]),
    # Qt-хуки PyInstaller добавляют необходимые плагины и перевод qtbase_ru.
    hiddenimports=["cyberlab.diagnostics"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets"],
    noarchive=False,
)
archive = PYZ(analysis.pure)
executable = EXE(
    archive,
    analysis.scripts,
    *([analysis.binaries, analysis.datas] if windows else []),
    exclude_binaries=not windows,
    name="CyberLab",
    console=False,
    debug=False,
    strip=False,
    upx=False,
    icon=str(root / "src" / "cyberlab" / "resources" / "cyberlab.ico") if windows else None,
)
if not windows:
    collection = COLLECT(
        executable,
        analysis.binaries,
        analysis.datas,
        strip=False,
        upx=False,
        name="CyberLab",
    )
