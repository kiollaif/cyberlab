from dataclasses import replace

import pytest

from cyberlab.domain import ComputerState
from cyberlab.mentor import explain_comparison, explain_state
from cyberlab.scenarios import PHISHING


@pytest.mark.parametrize(
    ("choices", "expected_text"),
    [
        ((), "риск: 0/100"),
        (("inspect",), "Адрес отправителя проверен"),
        (("open_link",), "пароль ещё не отправлен"),
        (("open_link", "submit", "ignore"), "Виртуальные файлы зашифрованы"),
        (("open_link", "submit", "isolate"), "Учебная сеть отключена"),
        (("report",), "Письмо в карантине"),
    ],
)
def test_mentor_explains_actual_scenario_snapshots(choices, expected_text):
    node_id = PHISHING.start_node
    state = ComputerState()
    for choice_id in choices:
        next_node, state, _ = PHISHING.advance(node_id, state, choice_id)
        node_id = next_node.id
    assert expected_text in explain_state(state)


def test_comparison_uses_snapshot_values_and_correct_direction():
    damage = ComputerState(risk=100, credentials_exposed=True, files_encrypted=True)
    safe = ComputerState(email_quarantined=True)
    explanation = explain_comparison(damage, safe)
    assert "A — 100 / 100; B — 0 / 100" in explanation
    assert "Файлы: A — Зашифрованы; B — Доступны" in explanation
    assert "риск ниже" in explanation
    assert "риск выше" in explain_comparison(safe, damage)


def test_equal_metrics_do_not_imply_equal_decision_history():
    original = ComputerState()
    different_history = replace(original, events=("Другой путь",))
    assert "снимки совпадают" in explain_comparison(original, different_history)
    assert original.events != different_history.events
