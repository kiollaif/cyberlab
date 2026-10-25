import os
import subprocess
import sys
from pathlib import Path


def test_offline_gui_and_sqlite_with_network_guard(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts" / "smoke_offline.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Offline smoke passed" in result.stdout
