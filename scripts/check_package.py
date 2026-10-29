"""Установить собранный wheel из кэша и проверить его вне исходного каталога."""

import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def run(arguments: list[str], *, cwd: Path | None = None) -> None:
    result = subprocess.run(arguments, cwd=cwd, capture_output=True, text=True)
    print(result.stdout, end="")
    print(result.stderr, end="", file=sys.stderr)
    if result.returncode:
        raise RuntimeError(
            f"{arguments[0]} exited with {result.returncode}:\n"
            + (result.stdout + result.stderr)[-10000:]
        )


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    wheels = list((root / "dist").glob("cyberlab-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError("В dist должен быть один wheel CYBERLAB. Сначала выполните uv build.")
    with TemporaryDirectory(prefix="cyberlab-package-") as directory:
        workspace = Path(directory)
        environment = workspace / "venv"
        run(["uv", "venv", "--python", sys.executable, str(environment)])
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        # uv sync использует адреса wheel из uv.lock и может не кэшировать индекс PyPI.
        # pylock сохраняет адреса и хеши: офлайн-установка не ищет версии в индексе.
        locked_dependencies = workspace / "pylock.toml"
        run(
            [
                "uv",
                "--quiet",
                "export",
                "--locked",
                "--offline",
                "--no-dev",
                "--no-emit-project",
                "--format",
                "pylock.toml",
                "--output-file",
                str(locked_dependencies),
            ],
            cwd=root,
        )
        run(["uv", "pip", "sync", "--offline", "--python", str(python), str(locked_dependencies)])
        run(
            [
                "uv",
                "pip",
                "install",
                "--offline",
                "--no-deps",
                "--python",
                str(python),
                str(wheels[0]),
            ]
        )
        run(["uv", "pip", "check", "--python", str(python)])
        run([str(python), "-m", "cyberlab", "--help"], cwd=workspace)
        run(
            [str(python), str(root / "scripts" / "smoke_offline.py"), "--installed"],
            cwd=workspace,
        )
        report = workspace / "four-scenarios.json"
        run([str(python), "-m", "cyberlab", "--smoke-test", str(report)], cwd=workspace)
        result = json.loads(report.read_text(encoding="utf-8"))
        assert result["success"] and not result["network_attempts"], result
        print("Installed wheel: four scenarios, alternatives, TXT report and SQLite passed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        if os.environ.get("GITHUB_ACTIONS"):
            message = str(error).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
            print(f"::error title=Installed package::{message}")
        raise
