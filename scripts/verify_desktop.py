"""Запустить готовую сборку из пустого рабочего каталога и проверить JSON-отчёт."""

import argparse
import json
import os
import struct
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory


def assert_no_console(executable: Path) -> None:
    with executable.open("rb") as stream:
        stream.seek(0x3C)
        pe_offset = struct.unpack("<I", stream.read(4))[0]
        stream.seek(pe_offset)
        assert stream.read(4) == b"PE\0\0", "Не является исполняемым файлом Windows"
        stream.seek(pe_offset + 24 + 68)
        assert struct.unpack("<H", stream.read(2))[0] == 2, "EXE собран с консолью"


def verify(executable: Path, report: Path) -> None:
    # Сохраняем симлинк /usr/bin/cyberlab: проверяем именно путь ярлыка RPM.
    executable = executable.absolute()
    report = report.resolve()
    with TemporaryDirectory(prefix="CyberLab launch with spaces ") as directory:
        work = Path(directory)
        env = dict(os.environ)
        env.pop("DEEPSEEK_API_KEY", None)
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
        # Только системные утилиты: запуск не должен зависеть от Python/uv в PATH.
        env["PATH"] = (
            str(Path(os.environ["SystemRoot"]) / "System32") if os.name == "nt" else "/usr/bin:/bin"
        )
        if os.name != "nt":
            for name in ("XDG_DATA_HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME"):
                env[name] = str(work / name.lower())
        result = subprocess.run(
            [str(executable), "--smoke-test", str(report)],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=150,
        )
        if result.returncode or not report.exists():
            raise RuntimeError(
                f"{executable.name}: exit={result.returncode}\n"
                f"{result.stdout[-2000:]}\n{result.stderr[-6000:]}"
            )
        data = json.loads(report.read_text(encoding="utf-8"))
        if not data.get("success"):
            raise RuntimeError(json.dumps(data, ensure_ascii=False, indent=2))
        assert data["frozen"], "Проверялся исходный код, а не сборка"
        assert not data["network_attempts"]
        if os.name == "nt":
            assert_no_console(executable)
            assert Path(data["data_directory"]).is_relative_to(Path(os.environ["LOCALAPPDATA"]))
        else:
            assert Path(data["data_directory"]).is_relative_to(Path(env["XDG_DATA_HOME"]))
        print(json.dumps(data, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    verify(args.executable, args.report)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        if os.environ.get("GITHUB_ACTIONS"):
            message = str(error).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
            print(f"::error title=Desktop executable::{message}")
        raise
