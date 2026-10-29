"""Подготовка только уже известных учебных данных. Здесь нет сети и записи в SQLite."""

import json
from dataclasses import dataclass

from cyberlab.domain import ComputerState, Scenario
from cyberlab.learning import decision_rating, history_path
from cyberlab.mentor import explain_comparison, explain_state, explain_step
from cyberlab.storage import HistoryEntry

MAX_CONTEXT_CHARS = 8000


@dataclass(frozen=True)
class MentorContext:
    key: str
    payload: str
    local_state: str
    local_decision: str
    local_analysis: str
    local_comparison: str = ""

    def fallback(self, task: str) -> str:
        if task == "decision":
            return self.local_decision
        if task == "analysis":
            return self.local_analysis
        if task == "comparison" and self.local_comparison:
            return self.local_comparison
        return self.local_state


def computer_data(state: ComputerState) -> dict:
    # Явный список исключает случайную передачу новых полей в будущем.
    return {
        "risk": state.risk,
        "credentials_exposed": state.credentials_exposed,
        "files_encrypted": state.files_encrypted,
        "network_connected": state.network_connected,
        "email_quarantined": state.email_quarantined,
        "email_inspected": state.email_inspected,
        "browser_open": state.browser_open,
        "attachment_opened": state.attachment_opened,
        "macros_enabled": state.macros_enabled,
        "usb_connected": state.usb_connected,
        "malware_active": state.malware_active,
        "source_verified": state.source_verified,
        "threat_blocked": state.threat_blocked,
    }


def branch_data(scenario: Scenario, entries: list[HistoryEntry], active: HistoryEntry) -> dict:
    path = history_path(entries, active.id)
    decisions = []
    for before, after in zip(path, path[1:], strict=False):
        decisions.append(
            {
                "action": after.choice_title[:120],
                "consequence": after.state.events[-1][:200],
                "risk_before": before.state.risk,
                "risk_after": after.state.risk,
            }
        )
    return {
        "situation": scenario.node(active.node_id).title[:200],
        "description": scenario.node(active.node_id).description[:800],
        "computer": computer_data(active.state),
        "decisions": decisions[-4:],
    }


def build_context(
    scenario: Scenario,
    entries: list[HistoryEntry],
    active: HistoryEntry,
    comparison: tuple[HistoryEntry, HistoryEntry] | None = None,
) -> MentorContext:
    path = history_path(entries, active.id)
    decision = "Вы ещё не приняли решение.\n\n" + explain_state(active.state, scenario)
    analysis = []
    for before, after in zip(path, path[1:], strict=False):
        explanation = explain_step(scenario, before, after)
        analysis.append(
            f"{decision_rating(before.state, after.state)}: {after.choice_title}. {explanation}"
        )
        decision = f"Вы выбрали: {after.choice_title}.\n\n{explanation}"
    data = {"current": branch_data(scenario, entries, active)}
    key = active.id
    local_comparison = ""
    if comparison is not None:
        left, right = comparison
        data["comparison"] = [branch_data(scenario, entries, entry) for entry in comparison]
        key += f":{left.id}:{right.id}"
        local_comparison = explain_comparison(left.state, right.state, scenario)
    # Не сериализуем Scenario целиком: будущих узлов, значений риска и событий
    # непройденных веток в запросе нет. Содержимое файлов ПК и идентификаторы БД не нужны.
    return MentorContext(
        key=key,
        payload=json.dumps(data, ensure_ascii=False)[:MAX_CONTEXT_CHARS],
        local_state=explain_state(active.state, scenario),
        local_decision=decision,
        local_analysis="\n\n".join(analysis)
        or "Решений пока нет. " + explain_state(active.state, scenario),
        local_comparison=local_comparison,
    )
