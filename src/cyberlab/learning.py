"""Подготовка учебных итогов из настоящих снимков. Здесь нет Qt и записи в БД."""

from cyberlab.domain import ComputerState, Scenario
from cyberlab.storage import HistoryEntry


def history_path(entries: list[HistoryEntry], entry_id: str) -> list[HistoryEntry]:
    """Собрать только предков выбранного снимка, от начала до результата."""
    entries_by_id = {entry.id: entry for entry in entries}
    path = []
    visited = set()
    # Идём по parent_id назад, затем разворачиваем список. Соседние ветки
    # не попадают в разбор решений, даже если созданы раньше выбранного итога.
    while entry_id is not None:
        if entry_id in visited or entry_id not in entries_by_id:
            raise ValueError("Не удалось восстановить путь решений.")
        visited.add(entry_id)
        entry = entries_by_id[entry_id]
        path.append(entry)
        entry_id = entry.parent_id
    return list(reversed(path))


def remaining_decisions(scenario: Scenario, node_id: str) -> int:
    """Наибольшее число выборов до итога: короткая ветка закончится раньше."""

    def count(current_id: str, visited: set[str]) -> int:
        if current_id in visited:
            raise ValueError("Для прогресса нужен сценарий без циклов.")
        choices = scenario.node(current_id).choices
        if not choices:
            return 0
        return 1 + max(count(choice.next_node, visited | {current_id}) for choice in choices)

    return count(node_id, set())


def risk_level(risk: int) -> str:
    if risk >= 60:
        return "Высокий"
    if risk >= 25:
        return "Повышенный"
    return "Низкий"


def decision_rating(before: ComputerState, after: ComputerState) -> str:
    """Оценить изменение, а не объявлять всю ветку правильной или неправильной."""
    if (
        after.risk > before.risk
        or (after.credentials_exposed and not before.credentials_exposed)
        or (after.files_encrypted and not before.files_encrypted)
        or (after.malware_active and not before.malware_active)
    ):
        return "Риск вырос"
    if (
        after.risk < before.risk
        or (after.email_inspected and not before.email_inspected)
        or (after.email_quarantined and not before.email_quarantined)
        or (after.source_checked and not before.source_checked)
        or (after.threat_blocked and not before.threat_blocked)
    ):
        return "Полезное решение"
    return "Без изменения риска"


def state_summary(state: ComputerState) -> str:
    """Короткий итог по наблюдаемым данным, без прогноза будущих событий."""
    if state.files_encrypted:
        password = "Учебный пароль раскрыт" if state.credentials_exposed else "Пароль не раскрыт"
        return f"{password}, доступ к виртуальным файлам потерян."
    if state.malware_active:
        return "В модели работает подозрительная программа. Файлы пока доступны."
    if state.credentials_exposed:
        return "Учебный пароль раскрыт. Виртуальные файлы пока доступны."
    if state.email_quarantined:
        return "Письмо изолировано. Пароль и виртуальные файлы защищены."
    if state.threat_blocked:
        return "Угроза остановлена. Пароль и виртуальные файлы защищены."
    if state.browser_open:
        return "Открыта страница из письма. Учебный пароль ещё не отправлен."
    return "Пароль и файлы защищены. Источник требует проверки."
