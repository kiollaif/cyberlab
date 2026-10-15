from dataclasses import FrozenInstanceError

import pytest

from cyberlab.domain import ComputerState, compare_states
from cyberlab.scenarios import PHISHING


def play(*choices: str) -> tuple[str, ComputerState]:
    node, state = PHISHING.node(PHISHING.start_node), ComputerState()
    for choice in choices:
        node, state, _ = PHISHING.advance(node.id, state, choice)
    return node.id, state


@pytest.mark.parametrize("prefix", [(), ("inspect",)])
@pytest.mark.parametrize(
    ("decisions", "ending", "risk", "exposed", "encrypted", "connected"),
    [
        (("report",), "reported", 0, False, False, True),
        (("open_link", "close_report"), "contained", 10, False, False, True),
        (("open_link", "submit", "isolate"), "isolated", 40, True, False, False),
        (("open_link", "submit", "ignore"), "damage", 100, True, True, True),
    ],
)
def test_every_scenario_path(prefix, decisions, ending, risk, exposed, encrypted, connected):
    node_id, state = play(*prefix, *decisions)
    assert node_id == ending
    assert PHISHING.node(node_id).terminal
    assert state.risk == risk
    assert state.credentials_exposed is exposed
    assert state.files_encrypted is encrypted
    assert state.network_connected is connected
    assert len(state.events) == 1 + len(prefix) + len(decisions)


def test_invalid_decision_does_not_change_original_snapshot():
    initial = ComputerState()
    with pytest.raises(ValueError, match="недоступно"):
        PHISHING.advance("inbox", initial, "submit")
    assert initial == ComputerState()
    with pytest.raises(FrozenInstanceError):
        initial.risk = 100


def test_terminal_node_rejects_further_decisions():
    node, state = play("report")
    with pytest.raises(ValueError, match="недоступно"):
        PHISHING.advance(node, state, "open_link")


def test_scenario_graph_has_no_dead_links_or_unreachable_nodes():
    visited = set()

    def walk(node_id, ancestors):
        assert node_id not in ancestors, "Первый сценарий должен завершаться"
        node = PHISHING.node(node_id)
        visited.add(node.id)
        assert len({choice.id for choice in node.choices}) == len(node.choices)
        for choice in node.choices:
            walk(choice.next_node, ancestors | {node_id})

    walk(PHISHING.start_node, set())
    assert visited == {node.id for node in PHISHING.nodes}


def test_comparison_explains_alternative_consequences():
    _, damage = play("open_link", "submit", "ignore")
    _, safe = play("report")
    rows = {row.label: row for row in compare_states(damage, safe)}
    assert (rows["Учебный риск"].left, rows["Учебный риск"].right) == ("100 / 100", "0 / 100")
    assert (rows["Файлы"].left, rows["Файлы"].right) == ("Зашифрованы", "Доступны")
    assert rows["Учётные данные"].different
    assert not rows["Сеть"].different


@pytest.mark.parametrize("risk", [-1, 101])
def test_risk_bounds(risk):
    with pytest.raises(ValueError):
        ComputerState(risk=risk)
