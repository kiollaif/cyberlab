import os

import pytest

# Позволяет запускать настоящий Qt без дисплея на Linux и в Windows CI.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def isolated_api_environment(monkeypatch):
    """Личный ключ и выбранный поставщик не должны влиять на тесты или тратить деньги."""
    for name in tuple(os.environ):
        if name == "DEEPSEEK_API_KEY" or name.startswith("CYBERLAB_AI_"):
            monkeypatch.delenv(name, raising=False)
