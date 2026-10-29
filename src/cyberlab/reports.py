"""Текстовый отчёт по одному фактически сохранённому пути, без Qt и сети."""

from cyberlab.domain import Scenario
from cyberlab.learning import history_path, state_summary
from cyberlab.mentor import explain_step
from cyberlab.storage import HistoryEntry


def build_report(scenario: Scenario, entries: list[HistoryEntry], active: HistoryEntry) -> str:
    path = history_path(entries, active.id)
    risks = [entry.state.risk for entry in path]
    status = "Ветка завершена" if scenario.node(active.node_id).terminal else "Промежуточный шаг"
    lines = [
        "CYBERLAB — учебный отчёт",
        f"Сценарий: {scenario.title}",
        f"Состояние: {status}",
        f"Текущий итог: {scenario.node(active.node_id).title}",
        f"Решений: {len(path) - 1}. Максимальный риск: {max(risks)}/100.",
        "Динамика риска: " + " → ".join(map(str, risks)),
        "Риск — условная учебная шкала, не вероятность атаки.",
        "",
        "Решения выбранного пути",
    ]
    for number, (before, after) in enumerate(zip(path, path[1:], strict=False), 1):
        lines.extend(
            [
                f"{number}. {after.choice_title}",
                f"   Последствие: {after.state.events[-1]}",
                f"   Риск: {before.state.risk} → {after.state.risk}",
                f"   Почему: {explain_step(scenario, before, after)}",
            ]
        )
    if len(path) == 1:
        lines.append("Решения ещё не приняты.")
    lines.extend(
        [
            "",
            "Итог состояния",
            state_summary(active.state),
            "",
            "Отчёт описывает только выбранный путь. Другие ветки остались в истории.",
            "Все события учебные. Реальные пароли, файлы и устройства не использовались.",
        ]
    )
    return "\n".join(lines) + "\n"
