"""Тот же вход, который проверяет EXE/AppImage: шесть тем без сетевых запросов."""

import json
import os
import subprocess
import sys

from cyberlab import __version__


def test_desktop_diagnostic_visits_all_scenarios_and_exports_pdf(tmp_path):
    report = tmp_path / "desktop.json"
    result = subprocess.run(
        [sys.executable, "-m", "cyberlab", "--smoke-test", str(report)],
        env=os.environ.copy(),
        text=True,
        capture_output=True,
        timeout=45,
    )
    assert result.returncode == 0, (
        result.stdout + result.stderr + (report.read_text() if report.exists() else "")
    )
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["success"] and not data["network_attempts"]
    assert data["version"] == __version__
    assert any("six scenarios" in item and "TXT/PDF" in item for item in data["checks"])
