"""Учебные примеры должны запускаться, а не только выглядеть правдоподобно."""

import re
from pathlib import Path

import pytest

GUIDE_PATH = Path(__file__).resolve().parents[1] / "STUDY_GUIDE.md"
EXAMPLES = re.findall(r"```python\n(.*?)\n```", GUIDE_PATH.read_text(encoding="utf-8"), re.DOTALL)


def test_guide_contains_at_least_five_runnable_examples():
    assert len(EXAMPLES) >= 5


@pytest.mark.parametrize("source", EXAMPLES, ids=lambda source: source.splitlines()[0])
def test_study_example_runs_with_current_project(source):
    # У каждого примера собственные имена: случайная переменная из предыдущего
    # блока не должна скрыть недостающий import или ошибку учебной инструкции.
    namespace = {"__name__": "__study_example__"}
    exec(compile(source, str(GUIDE_PATH), "exec"), namespace)
