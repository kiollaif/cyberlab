"""Единая оценка фактических решений для экрана итогов, истории и отчёта."""

from dataclasses import dataclass

from cyberlab.domain import Scenario
from cyberlab.learning import decision_rating, history_path
from cyberlab.mentor import explain_step
from cyberlab.storage import HistoryEntry


@dataclass(frozen=True)
class DecisionReview:
    title: str
    rating: str
    explanation: str
    risk_before: int
    risk_after: int
    recommendation: str = ""


@dataclass(frozen=True)
class Assessment:
    safe: int
    risky: int
    neutral: int
    score: int | None
    risks: tuple[int, ...]
    decisions: tuple[DecisionReview, ...]

    @property
    def mistakes(self) -> tuple[DecisionReview, ...]:
        return tuple(item for item in self.decisions if item.rating == "Риск вырос")


def assess_path(
    scenario: Scenario, entries: list[HistoryEntry], active: HistoryEntry
) -> Assessment:
    path = history_path(entries, active.id)
    reviews = []
    safe = risky = neutral = 0
    for before, after in zip(path, path[1:], strict=False):
        rating = decision_rating(before.state, after.state)
        recommendation = ""
        if rating == "Риск вырос":
            risky += 1
            alternatives = []
            for choice in scenario.node(before.node_id).choices:
                if choice.id == after.choice_id:
                    continue
                _, alternative, _ = scenario.advance(before.node_id, before.state, choice.id)
                if decision_rating(before.state, alternative) == "Полезное решение":
                    alternatives.append(choice.title)
            recommendation = (
                "На этом шаге можно было выбрать: " + "; ".join(alternatives) + "."
                if alternatives
                else "Остановитесь и проверьте источник через известный контакт."
            )
        elif rating == "Полезное решение":
            safe += 1
        else:
            neutral += 1
        reviews.append(
            DecisionReview(
                title=after.choice_title,
                rating=rating,
                explanation=explain_step(scenario, before, after),
                risk_before=before.state.risk,
                risk_after=after.state.risk,
                recommendation=recommendation,
            )
        )
    # За полезное решение — 2 балла, за нейтральное — 1, за рискованное — 0.
    # Отдельно показываем итоговый риск: позднее исправление не стирает прежние ошибки.
    total = safe + risky + neutral
    score = round(100 * (2 * safe + neutral) / (2 * total)) if total else None
    return Assessment(
        safe, risky, neutral, score, tuple(item.state.risk for item in path), tuple(reviews)
    )
