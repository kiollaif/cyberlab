"""Чтение истории без новых таблиц: оценки восстанавливаются из сохранённых решений."""

from dataclasses import dataclass

from cyberlab.assessment import assess_path
from cyberlab.domain import Scenario
from cyberlab.storage import HistoryRepository


@dataclass(frozen=True)
class ResultRecord:
    scenario_id: str
    session_id: str
    entry_id: str
    created_at: str
    title: str
    completed: bool
    risk: int
    score: int | None
    safe: int
    risky: int
    decisions: int


def load_results(
    repository: HistoryRepository, scenarios: tuple[Scenario, ...]
) -> list[ResultRecord]:
    known = {scenario.id: scenario for scenario in scenarios}
    records = []
    for session in repository.sessions():
        scenario = known.get(session.scenario_id)
        if scenario is None:
            continue
        entries = repository.entries(session.id)
        completed = [entry for entry in entries if scenario.node(entry.node_id).terminal]
        active = repository.entry(session.active_entry_id, session.id)
        # Сохраняем в списке каждый завершённый вариант, даже после возврата к корню.
        # Текущий незавершённый путь показываем отдельно, если в нём уже есть решения.
        candidates = completed + ([active] if active.parent_id and active not in completed else [])
        for entry in candidates:
            assessment = assess_path(scenario, entries, entry)
            records.append(
                ResultRecord(
                    scenario_id=scenario.id,
                    session_id=session.id,
                    entry_id=entry.id,
                    created_at=entry.created_at,
                    title=scenario.node(entry.node_id).title,
                    completed=scenario.node(entry.node_id).terminal,
                    risk=entry.state.risk,
                    score=assessment.score,
                    safe=assessment.safe,
                    risky=assessment.risky,
                    decisions=len(assessment.decisions),
                )
            )
    return sorted(records, key=lambda item: item.created_at, reverse=True)
