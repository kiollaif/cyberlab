"""Каждый маршрут новых графов завершается; возврат и SQLite не смешивают сценарии."""

from dataclasses import asdict

import pytest

from cyberlab.domain import ComputerState
from cyberlab.mentor import explain_state, explain_step
from cyberlab.scenarios import SCENARIOS, get_scenario
from cyberlab.session import LabSession
from cyberlab.storage import HistoryRepository


def routes(scenario, node_id=None, decisions=(), ancestors=frozenset()):
    node = scenario.node(node_id or scenario.start_node)
    assert node.id not in ancestors
    assert len({choice.id for choice in node.choices}) == len(node.choices)
    if node.terminal:
        yield decisions
    for choice in node.choices:
        yield from routes(
            scenario, choice.next_node, decisions + (choice.id,), ancestors | {node.id}
        )


ALL_ROUTES = [(scenario, path) for scenario in SCENARIOS for path in routes(scenario)]


@pytest.mark.parametrize(
    "scenario,path", ALL_ROUTES, ids=[s.id + ":" + "/".join(p) for s, p in ALL_ROUTES]
)
def test_all_registered_routes_and_restart(tmp_path, scenario, path):
    database = tmp_path / "routes.sqlite3"
    repository = HistoryRepository(database)
    lab = LabSession(repository, scenario)
    initial = lab.active
    visited = {initial.node_id}
    for decision in path:
        before = lab.active
        after = lab.choose(decision)
        assert 0 <= after.state.risk <= 100
        assert len(after.state.events) == len(before.state.events) + 1
        assert explain_step(scenario, before, after)
        visited.add(after.node_id)
    assert lab.node.terminal
    terminal = lab.active
    if terminal.state.files_encrypted and scenario.kind in ("usb", "attachment"):
        assert not terminal.state.credentials_exposed
        assert "не раскрыт" in explain_state(terminal.state, scenario)
    lab.go_to(initial.id)
    count = len(lab.entries)
    for decision in path:
        lab.choose(decision)
    assert len(lab.entries) == count and lab.active == terminal
    repository.close()
    reopened = HistoryRepository(database)
    try:
        restored = LabSession(reopened, scenario)
        assert restored.active == terminal
        assert restored.entries[0].state.events == (scenario.initial_event,)
    finally:
        reopened.close()


def test_every_node_is_reachable():
    for scenario in SCENARIOS:
        reached = {scenario.start_node}
        for path in routes(scenario):
            node = scenario.node(scenario.start_node)
            for decision in path:
                node = scenario.node(next(c.next_node for c in node.choices if c.id == decision))
                reached.add(node.id)
        assert reached == {node.id for node in scenario.nodes}
        assert get_scenario(scenario.id) is scenario
        if scenario.kind != "phishing":
            assert all(c.explanation for n in scenario.nodes for c in n.choices)


def test_switching_scenarios_preserves_each_active_branch(tmp_path):
    repository = HistoryRepository(tmp_path / "mixed.sqlite3")
    try:
        lab = LabSession(repository)
        original = lab.choose("open_link")
        for scenario in SCENARIOS[1:]:
            lab.switch_scenario(scenario)
            lab.choose(lab.node.choices[0].id)
        lab.switch_scenario(SCENARIOS[0])
        assert lab.active == original
        assert len(repository.sessions(SCENARIOS[0].id)) == 1
        before = lab.active
        with pytest.raises(ValueError):
            lab.open_session(repository.sessions(SCENARIOS[1].id)[0].id)
        assert lab.active == before
        # Старые JSON не обязаны иметь новые ключи: dataclass даёт безопасные defaults.
        old_fields = asdict(ComputerState())
        for key in (
            "attachment_opened",
            "macros_enabled",
            "usb_connected",
            "malware_active",
            "source_verified",
            "threat_blocked",
        ):
            del old_fields[key]
        assert ComputerState(**old_fields) == ComputerState()
    finally:
        repository.close()
