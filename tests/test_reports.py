"""Экспорт содержит только фактический выбранный путь, не соседние ветки."""

from cyberlab.reports import build_report
from cyberlab.scenarios import SCENARIOS
from cyberlab.session import LabSession
from cyberlab.storage import HistoryRepository


def test_report_uses_active_path_risk_and_actual_consequences():
    repository = HistoryRepository(":memory:")
    try:
        lab = LabSession(repository)
        root = lab.active.id
        lab.choose("open_link")
        lab.choose("submit")
        damage = lab.choose("ignore")
        damaged_text = build_report(lab.scenario, lab.entries, damage)
        assert "0 → 30 → 75 → 100" in damaged_text
        assert "Максимальный риск: 100" in damaged_text
        assert damage.state.events[-1] in damaged_text
        lab.go_to(root)
        safe = lab.choose("report")
        before = lab.entries
        safe_text = build_report(lab.scenario, lab.entries, safe)
        assert "Динамика риска: 0 → 0" in safe_text
        assert "Отправить учебный пароль" not in safe_text
        assert lab.entries == before and lab.active == safe
    finally:
        repository.close()


def test_report_for_each_scenario_does_not_invent_a_password_leak():
    repository = HistoryRepository(":memory:")
    try:
        for scenario in SCENARIOS:
            lab = LabSession(repository, scenario)
            text = build_report(scenario, lab.entries, lab.active)
            assert scenario.title in text and "Решения ещё не приняты" in text
            assert "Промежуточный шаг" in text
            if scenario.kind in ("usb", "attachment"):
                while not lab.node.terminal:
                    lab.choose(lab.node.choices[-1].id)
                assert not lab.active.state.credentials_exposed
                assert "Учебный пароль раскрыт" not in build_report(
                    scenario, lab.entries, lab.active
                )
    finally:
        repository.close()
