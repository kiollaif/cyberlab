"""Локальные объяснения по правилам; они доступны и без внешнего API.

Модуль только читает снимки: он не выбирает решения, не меняет риск и не пишет в БД.
"""

from cyberlab.domain import ComputerState, Scenario, compare_states


def answer_local_question(question: str, current_explanation: str) -> str:
    """Небольшой открытый словарь правил, а не имитация генеративного ИИ."""
    rules = {
        "макрос": "Макросы выполняют команды. "
        "Не разрешайте их неожиданному документу без проверки.",
        "usb": "Чужой USB передайте специалисту. "
        "Отключение USB не останавливает уже запущенную программу.",
        "накопител": "Не подключайте неизвестное устройство к рабочему ПК "
        "для проверки его содержимого.",
        "https": "HTTPS шифрует соединение, "
        "но не доказывает, что сайт принадлежит школе или банку.",
        "парол": "Не вводите настоящий пароль в симуляцию. После утечки используют "
        "доверенный канал для смены пароля и отзыва сеансов.",
        "фишинг": "Фишинг убеждает довериться чужому источнику. "
        "Проверяйте домен и обращайтесь через известный контакт.",
        "риск": "Риск 0–100 — учебная оценка автора сценария, а не вероятность реальной атаки.",
    }
    for keyword, explanation in rules.items():
        if keyword in question.lower():
            return explanation + "\n\nТекущая симуляция\n" + current_explanation
    return current_explanation


def explain_state(state: ComputerState, scenario: Scenario | None = None) -> str:
    """Объяснить наблюдаемые последствия текущей ветки простыми словами."""
    paragraphs = [f"Учебный риск: {state.risk}/100. Это условная шкала сценария."]
    if scenario is not None and scenario.kind != "phishing":
        paragraphs.append(state.events[-1])
        paragraphs.append(
            "Учебный пароль раскрыт." if state.credentials_exposed else "Учебный пароль не раскрыт."
        )
        if state.malware_active:
            paragraphs.append(
                "В модели работает подозрительная программа. Нужна помощь специалиста."
            )
        if state.files_encrypted:
            paragraphs.append("Виртуальные файлы недоступны. Реальные файлы не изменялись.")
        if state.threat_blocked:
            paragraphs.append(
                "Угроза остановлена в этом снимке; прошлые события остаются в истории."
            )
        if scenario.kind == "usb":
            paragraphs.append(
                "Учебный USB подключён." if state.usb_connected else "USB не подключён."
            )
            paragraphs.append(
                "Проверку неизвестного устройства поручают специалисту, не запуская файлы."
            )
        elif scenario.kind == "attachment":
            paragraphs.append(
                "Не разрешайте макросы неожиданному документу без проверки источника."
            )
        else:
            paragraphs.append(
                "Проверяйте точный домен. HTTPS сам по себе не подтверждает владельца."
            )
        return "\n\n".join(paragraphs)

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


def explain_comparison(
    left: ComputerState, right: ComputerState, scenario: Scenario | None = None
) -> str:
    """Описать разницу A → B по тем же пяти показателям, что и таблица интерфейса."""
    differences = []
    for row in compare_states(left, right, scenario):
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


def explain_step(scenario: Scenario, before, after) -> str:
    """Объяснение берётся у уже выбранного действия, не у будущих узлов графа."""
    for choice in scenario.node(before.node_id).choices:
        if choice.id == after.choice_id and choice.explanation:
            return choice.explanation
    return explain_decision(after.choice_id, before.state, after.state)


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
