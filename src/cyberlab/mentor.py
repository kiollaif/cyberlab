"""Локальные объяснения по правилам. Генеративная AI-модель пока не подключена.

Модуль только читает снимки: он не выбирает решения, не меняет риск и не пишет в БД.
"""

from cyberlab.domain import ComputerState, compare_states


def explain_state(state: ComputerState) -> str:
    """Объяснить наблюдаемые последствия текущей ветки простыми словами."""
    paragraphs = [f"Учебный риск: {state.risk}/100. Это условная шкала сценария."]

    if state.credentials_exposed:
        paragraphs.append(
            "Учебный пароль раскрыт. Отключение сети не отменяет уже произошедшую утечку."
        )
    elif state.browser_open:
        paragraphs.append(
            "Поддельная страница открыта, но пароль ещё не отправлен. "
            "Обратите внимание на адрес: знакомый внешний вид не доказывает подлинность."
        )
    else:
        paragraphs.append("На этом снимке учётные данные защищены.")

    if state.files_encrypted:
        paragraphs.append(
            "Виртуальные файлы зашифрованы. Вернитесь к шагу до этого последствия "
            "и проверьте, какое решение помогло бы сохранить доступ к ним."
        )
    if not state.network_connected:
        paragraphs.append("Учебная сеть отключена. Это отдельный показатель, не смена пароля.")

    if state.email_quarantined:
        paragraphs.append("Письмо в карантине: оно изолировано в учебной модели.")
    elif state.email_inspected:
        paragraphs.append(
            "Адрес отправителя проверен. Сравните его домен с ожидаемым: "
            "отображаемое имя само по себе не подтверждает подлинность письма."
        )
    else:
        paragraphs.append("Проверьте адрес отправителя и цель ссылки до дальнейших действий.")

    return "\n\n".join(paragraphs)


def explain_comparison(left: ComputerState, right: ComputerState) -> str:
    """Описать разницу A → B по тем же пяти показателям, что и таблица интерфейса."""
    differences = []
    for row in compare_states(left, right):
        if row.different:
            differences.append(f"{row.label}: A — {row.left}; B — {row.right}.")

    if not differences:
        return (
            "По пяти сравниваемым показателям снимки совпадают. "
            "Пути к ним могут различаться: посмотрите дерево решений и журнал."
        )

    if right.risk < left.risk:
        differences.append("В ветке B учебный риск ниже, чем в A.")
    elif right.risk > left.risk:
        differences.append("В ветке B учебный риск выше, чем в A.")
    return "\n\n".join(differences)


def explain_decision(choice_id: str | None, before: ComputerState, after: ComputerState) -> str:
    """Объяснить уже совершённый выбор; вызывается только после его сохранения."""
    if after.files_encrypted and not before.files_encrypted:
        return (
            "Подозрительная активность осталась без ответа. В этом сценарии атака "
            "продолжилась и закрыла доступ к учебным файлам. Настоящие файлы не изменялись."
        )
    if after.credentials_exposed and not before.credentials_exposed:
        return (
            "Пароль отправлен на чужой сайт. Поэтому в модели его получил злоумышленник. "
            "Внешний вид страницы не подтверждает её подлинность."
        )
    if not after.network_connected and before.network_connected:
        return (
            "Отключение учебной сети остановило дальнейшую атаку. Уже раскрытый пароль "
            "остался раскрытым: в реальной ситуации его меняют через доверенный канал "
            "и завершают посторонние сеансы."
        )
    if after.email_quarantined and not before.email_quarantined:
        return (
            "Письмо изолировано после сообщения специалистам. "
            "Это остановило продвижение по подозрительной ссылке."
            + (" Вы успели закрыть страницу до отправки пароля." if before.browser_open else "")
        )
    if after.browser_open and not before.browser_open:
        return (
            "Ссылка привела на чужой домен. В модели открытие такой страницы повысило риск, "
            "но само по себе ещё не передало пароль."
        )
    if choice_id == "inspect":
        return (
            "Проверка показала настоящий адрес отправителя и цель ссылки. Они отличаются "
            "от cyberlab.example. Срочность и похожее имя помогают заметить обман."
        )
    return f"Зафиксировано событие: {after.events[-1]} Учебный риск: {before.risk} → {after.risk}."
