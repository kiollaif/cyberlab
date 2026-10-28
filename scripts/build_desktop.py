"""Собрать приложение с Python и Qt внутри, а не требовать их от пользователя."""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist" / "desktop"
TOOLS = {
    "appimagetool-x86_64.AppImage": (
        "https://github.com/AppImage/appimagetool/releases/download/1.9.0/"
        "appimagetool-x86_64.AppImage",
        "46fdd785094c7f6e545b61afcfb0f3d98d8eab243f644b4b17698c01d06083d1",
    ),
    "runtime-x86_64": (
        "https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-x86_64",
        "617aa77314d57c8b8e4fae9c3f0b35af7b30d5529cb69e98f64f92510ed98a46",
    ),
}


def run(arguments: list[str], **kwargs) -> None:
    subprocess.run(arguments, cwd=ROOT, check=True, **kwargs)


def download_tool(name: str) -> Path:
    cache = Path(os.environ.get("CYBERLAB_BUILD_CACHE", ROOT / "build" / "tools"))
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / name
    url, checksum = TOOLS[name]
    if not path.exists():
        with urllib.request.urlopen(url, timeout=120) as response, path.open("wb") as output:
            shutil.copyfileobj(response, output)
    if hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
        raise RuntimeError(f"Неверная контрольная сумма {name}; файл не будет выполнен")
    path.chmod(0o755)
    return path


def build_appimage() -> Path:
    appdir = ROOT / "build" / "CyberLab.AppDir"
    if appdir.exists():
        shutil.rmtree(appdir)
    bundle = appdir / "usr" / "lib" / "cyberlab"
    shutil.copytree(ROOT / "dist" / "frozen" / "CyberLab", bundle)
    shutil.copy2(ROOT / "packaging" / "linux" / "AppRun", appdir / "AppRun")
    (appdir / "AppRun").chmod(0o755)
    shutil.copy2(ROOT / "packaging" / "linux" / "cyberlab.desktop", appdir)
    resources = ROOT / "src" / "cyberlab" / "resources"
    shutil.copy2(resources / "cyberlab.png", appdir / "cyberlab.png")
    (appdir / ".DirIcon").symlink_to("cyberlab.png")
    binary = appdir / "usr" / "bin"
    binary.mkdir(parents=True)
    (binary / "cyberlab").symlink_to("../lib/cyberlab/CyberLab")
    tool = download_tool("appimagetool-x86_64.AppImage")
    runtime = download_tool("runtime-x86_64")
    image = DIST / "CyberLab-x86_64.AppImage"
    run(
        [
            str(tool),
            "--appimage-extract-and-run",
            "--no-appstream",
            "--runtime-file",
            str(runtime),
            "--mksquashfs-opt",
            "-processors",
            "--mksquashfs-opt",
            "2",
            str(appdir),
            str(image),
        ],
        env={**os.environ, "ARCH": "x86_64"},
    )
    image.chmod(0o755)
    return image


def write_checksums() -> None:
    artifacts = sorted(
        path for path in DIST.iterdir() if path.suffix in {".exe", ".AppImage", ".rpm"}
    )
    (DIST / "SHA256SUMS.txt").write_text(
        "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in artifacts),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-freeze", action="store_true")
    parser.add_argument("--checksums-only", action="store_true")
    args = parser.parse_args()
    DIST.mkdir(parents=True, exist_ok=True)
    if args.checksums_only:
        write_checksums()
        return
    if not args.skip_freeze:
        run(
            [
                sys.executable,
                "-m",
                "PyInstaller",
                "--noconfirm",
                "--clean",
                "--distpath",
                "dist/frozen",
                "--workpath",
                "build/pyinstaller",
                "packaging/CyberLab.spec",
            ]
        )
    if sys.platform == "win32":
        shutil.copy2(ROOT / "dist" / "frozen" / "CyberLab.exe", DIST)
    elif sys.platform.startswith("linux"):
        build_appimage()
    else:
        raise RuntimeError("Поддерживается сборка только на Windows и Linux x86_64")
    write_checksums()


if __name__ == "__main__":
    main()
