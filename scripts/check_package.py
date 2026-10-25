"""Установить собранный wheel из кэша и проверить его вне исходного каталога."""

import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    wheels = list((root / "dist").glob("cyberlab-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError("В dist должен быть один wheel CYBERLAB. Сначала выполните uv build.")
    with TemporaryDirectory(prefix="cyberlab-package-") as directory:
        workspace = Path(directory)
        environment = workspace / "venv"
        subprocess.run(["uv", "venv", "--python", sys.executable, str(environment)], check=True)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run(
            ["uv", "pip", "install", "--offline", "--python", str(python), str(wheels[0])],
            check=True,
        )
        subprocess.run([str(python), "-m", "cyberlab", "--help"], cwd=workspace, check=True)
        subprocess.run(
            [str(python), str(root / "scripts" / "smoke_offline.py"), "--installed"],
            cwd=workspace,
            check=True,
        )


if __name__ == "__main__":
    main()
