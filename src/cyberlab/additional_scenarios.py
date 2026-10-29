"Три учебных графа. Все вложения, сайты и устройства существуют только в модели."

from cyberlab.domain import Choice, Scenario, ScenarioNode, StateChange

ATTACHMENT = Scenario(
    id="attachment-v1",
    title="Вредоносное вложение",
    kind="attachment",
    summary=("Документ просит включить макросы. Решите, кому и чему можно доверять."),
    initial_event="Получено учебное письмо с неожиданным вложением.",
    mail_subject="Новые условия проекта",
    mail_body=("Во вложении условия проекта. Для просмотра автор просит включить макросы."),
    sender_address="project@documents-check.invalid",
    artifact="Условия_проекта.docm",
    start_node="received",
    nodes=(
        ScenarioNode(
            id="received",
            title="В письме — неожиданный документ",
            description=(
                "От неизвестного адреса пришёл файл "
                "«Условия_проекта.docm». Вы его не ждали. Все действия "
                "ниже относятся к вымышленному документу."
            ),
            choices=(
                Choice(
                    id="inspect",
                    title="Проверить источник",
                    hint="Уточнить отправителя известным способом",
                    next_node="checked",
                    event="Известный контакт не подтвердил отправку документа.",
                    change=StateChange(source_checked=True),
                    explanation=(
                        "Проверка через знакомый канал выявила несоответствие. "
                        "Имя файла не доказывает доверие."
                    ),
                ),
                Choice(
                    id="open_attachment",
                    title="Открыть учебное вложение",
                    hint="Посмотреть смоделированный запрос",
                    next_node="document",
                    event=("Открыт макет документа с запросом на включение макросов."),
                    change=StateChange(risk=25, attachment_opened=True),
                    explanation=(
                        "Просмотр ещё не запустил макросы, но вы приблизились к "
                        "опасному разрешению."
                    ),
                ),
                Choice(
                    id="quarantine",
                    title="Передать файл специалисту",
                    hint="Не открывать неизвестное вложение",
                    next_node="safe",
                    event="Вымышленное вложение изолировано без открытия.",
                    change=StateChange(threat_blocked=True, email_quarantined=True),
                    explanation=(
                        "Неожиданный файл не получил возможности выполнять "
                        "команды в учебной модели."
                    ),
                ),
            ),
        ),
        ScenarioNode(
            id="checked",
            title="Отправка не подтверждена",
            description=(
                "Название обещает рабочий документ, но известный вам "
                "контакт его не отправлял. Расширение .docm допускает "
                "макросы; само расширение ещё не доказывает заражение."
            ),
            choices=(
                Choice(
                    id="quarantine",
                    title="Изолировать вложение",
                    hint="Передать на проверку",
                    next_node="safe",
                    event="Неподтверждённое вложение помещено в карантин.",
                    change=StateChange(risk=0, threat_blocked=True, email_quarantined=True),
                    explanation=(
                        "Несоответствие источника — достаточная причина "
                        "остановиться и обратиться к специалисту."
                    ),
                ),
                Choice(
                    id="open_attachment",
                    title="Всё же открыть документ",
                    hint="Продолжить учебный эксперимент",
                    next_node="document",
                    event=("Несмотря на неподтверждённый источник открыт макет документа."),
                    change=StateChange(risk=25, attachment_opened=True),
                    explanation=(
                        "Проверка помогает только тогда, когда её результат "
                        "учитывают при следующем выборе."
                    ),
                ),
            ),
        ),
        ScenarioNode(
            id="document",
            title="Документ просит включить макросы",
            description=(
                "Текст скрыт за надписью «Включите содержимое». Макросы "
                "— программные команды, а не обычное разрешение читать "
                "текст. Ничего реально запускать не нужно."
            ),
            choices=(
                Choice(
                    id="enable_macros",
                    title="Разрешить учебные макросы",
                    hint="Смоделировать выполнение команд",
                    next_node="running",
                    event="В модели макросы запустили подозрительную программу.",
                    change=StateChange(risk=80, macros_enabled=True, malware_active=True),
                    explanation=(
                        "Разрешение макросов дало документу возможность "
                        "выполнять команды. Поэтому риск вырос."
                    ),
                ),
                Choice(
                    id="close",
                    title="Закрыть и сообщить",
                    hint="Не давать разрешение на выполнение",
                    next_node="safe",
                    event="Документ закрыт, выполнение макросов не разрешено.",
                    change=StateChange(risk=5, threat_blocked=True, email_quarantined=True),
                    explanation=(
                        "Вы остановились до выполнения команд; учебные файлы остались доступны."
                    ),
                ),
            ),
        ),
        ScenarioNode(
            id="running",
            title="Замечена подозрительная активность",
            description=(
                "В журнале учебного ПК появилась неизвестная программа. "
                "Можно ограничить её последствия."
            ),
            choices=(
                Choice(
                    id="isolate",
                    title="Изолировать ПК и сообщить",
                    hint="Остановить программу в модели",
                    next_node="contained",
                    event=("Учебная сеть отключена, подозрительная программа остановлена."),
                    change=StateChange(
                        risk=35, network_connected=False, malware_active=False, threat_blocked=True
                    ),
                    explanation=(
                        "Изоляция ограничила дальнейший ущерб, но уже "
                        "состоявшийся запуск требует проверки специалистом."
                    ),
                ),
                Choice(
                    id="ignore",
                    title="Продолжить работу",
                    hint="Оставить предупреждение без ответа",
                    next_node="damage",
                    event=("Учебная программа сделала виртуальные файлы недоступными."),
                    change=StateChange(risk=100, files_encrypted=True),
                    explanation=(
                        "Активная программа не была остановлена. Изменилось "
                        "только состояние виртуальных файлов."
                    ),
                ),
            ),
        ),
        ScenarioNode(
            id="safe",
            title="Выполнение предотвращено",
            description="Опасные команды не запущены. Учебные файлы доступны.",
        ),
        ScenarioNode(
            id="contained",
            title="Программа остановлена",
            description=("Файлы сохранены. Уже произошедший запуск нужно расследовать."),
        ),
        ScenarioNode(
            id="damage",
            title="Потерян доступ к учебным файлам",
            description=("Файлы недоступны только в модели. Пароль в этой ветке не отправлялся."),
        ),
    ),
)
FAKE_WEBSITE = Scenario(
    id="fake-website-v1",
    title="Поддельный сайт",
    kind="website",
    summary=("Похожий домен и форма входа. Проверьте адрес до передачи учебных данных."),
    initial_event=("В учебном поиске найден сайт, похожий на школьный портал."),
    mail_subject="Результат учебного поиска",
    mail_body=("Найден портал с похожим названием. Доверенный адрес школы — school.example."),
    sender_address="",
    site_address="https://school-login.invalid",
    artifact="Страница школьного портала",
    start_node="search",
    nodes=(
        ScenarioNode(
            id="search",
            title="В поиске найден знакомый портал",
            description=(
                "Название и значок похожи на школьный сайт. Никакие "
                "адреса не открываются в настоящей сети."
            ),
            choices=(
                Choice(
                    id="inspect",
                    title="Проверить адрес результата",
                    hint="Сравнить домен с известным адресом",
                    next_node="checked",
                    event=("Домен school-login.invalid отличается от школьного school.example."),
                    change=StateChange(source_checked=True),
                    explanation=(
                        "Важен точный домен. Значок и похожее название можно скопировать."
                    ),
                ),
                Choice(
                    id="open_link",
                    title="Открыть учебную страницу",
                    hint="Посмотреть макет формы входа",
                    next_node="login",
                    event="Открыт макет сайта с чужим доменом.",
                    change=StateChange(risk=30, browser_open=True),
                    explanation=(
                        "Переход к чужой форме увеличил риск, но сам по себе не раскрыл пароль."
                    ),
                ),
                Choice(
                    id="bookmark",
                    title="Использовать известную закладку",
                    hint="Пройти по заранее проверенному адресу",
                    next_node="safe",
                    event=("Выбран известный школьный адрес; поддельный результат отклонён."),
                    change=StateChange(source_checked=True, threat_blocked=True),
                    explanation=("Проверенная закладка не зависит от названия результата поиска."),
                ),
            ),
        ),
        ScenarioNode(
            id="checked",
            title="Домен отличается",
            description=(
                "Замок HTTPS означает шифрование соединения, но не принадлежность сайта школе."
            ),
            choices=(
                Choice(
                    id="bookmark",
                    title="Перейти по известной закладке",
                    hint="Не использовать чужую форму",
                    next_node="safe",
                    event="Поддельный сайт отклонён после сравнения доменов.",
                    change=StateChange(risk=0, threat_blocked=True),
                    explanation=("Вы учли результат проверки и не передали данные на чужой адрес."),
                ),
                Choice(
                    id="open_link",
                    title="Всё же открыть форму",
                    hint="Продолжить симуляцию",
                    next_node="login",
                    event="Открыта форма несмотря на несовпадение домена.",
                    change=StateChange(risk=30, browser_open=True),
                    explanation="HTTPS не устраняет обнаруженное несовпадение домена.",
                ),
            ),
        ),
        ScenarioNode(
            id="login",
            title="Форма просит пароль",
            description=(
                "Адрес school-login.invalid не принадлежит учебной "
                "школе. Вводить настоящий пароль нельзя; кнопка "
                "моделирует передачу вымышленных данных."
            ),
            choices=(
                Choice(
                    id="submit",
                    title="Отправить учебный пароль",
                    hint="Только действие внутри модели",
                    next_node="exposed",
                    event=("Вымышленный пароль передан владельцу поддельной страницы."),
                    change=StateChange(risk=75, credentials_exposed=True),
                    explanation=(
                        "Защищённое соединение доставило данные именно чужому "
                        "сайту. Поэтому пароль считается раскрытым."
                    ),
                ),
                Choice(
                    id="close",
                    title="Закрыть форму и сообщить",
                    hint="Остановиться до передачи данных",
                    next_node="safe",
                    event="Форма закрыта без отправки пароля.",
                    change=StateChange(risk=5, browser_open=False, threat_blocked=True),
                    explanation=(
                        "Вы остановились до утечки. Для входа следует "
                        "использовать известный школьный адрес."
                    ),
                ),
            ),
        ),
        ScenarioNode(
            id="exposed",
            title="В журнале появился чужой сеанс",
            description=(
                "После учебной отправки пароля появился посторонний "
                "вход. Нужно ограничить доступ к аккаунту."
            ),
            choices=(
                Choice(
                    id="revoke",
                    title="Отозвать сеансы через известный портал",
                    hint="Сообщить специалисту и сменить учебный пароль",
                    next_node="contained",
                    event=("Посторонние сеансы отозваны в модели через доверенный канал."),
                    change=StateChange(risk=25, browser_open=False, threat_blocked=True),
                    explanation=(
                        "Доступ ограничен, но факт прежней утечки остаётся в "
                        "истории. Нельзя менять пароль через подозрительную "
                        "форму."
                    ),
                ),
                Choice(
                    id="ignore",
                    title="Не реагировать",
                    hint="Оставить учебный сеанс открытым",
                    next_node="damage",
                    event="Посторонний сеанс сохранил доступ к учебному аккаунту.",
                    change=StateChange(risk=95),
                    explanation=(
                        "Раскрытый пароль и неотозванный сеанс оставили доступ "
                        "открытым. Файлы ПК при этом не шифровались."
                    ),
                ),
            ),
        ),
        ScenarioNode(
            id="safe",
            title="Данные не переданы",
            description="Поддельная форма отклонена. Учебный аккаунт защищён.",
        ),
        ScenarioNode(
            id="contained",
            title="Доступ ограничен после утечки",
            description=("Посторонние сеансы отозваны. Прежняя утечка остаётся фактом."),
        ),
        ScenarioNode(
            id="damage",
            title="Посторонний доступ сохраняется",
            description=("В этой модели скомпрометирован аккаунт, а не файловая система ПК."),
        ),
    ),
)
USB = Scenario(
    id="usb-v1",
    title="Подозрительный USB-накопитель",
    kind="usb",
    summary=("Найден чужой накопитель. Решите, подключать ли его и запускать ли файлы."),
    initial_event=("Рядом с учебным компьютером найден неизвестный USB-накопитель."),
    mail_subject="Найден неизвестный накопитель",
    sender_address="",
    site_address="",
    mail_body=("На корпусе надпись «Материалы урока». Владелец неизвестен."),
    artifact="USB «Материалы урока»",
    start_node="found",
    nodes=(
        ScenarioNode(
            id="found",
            title="Кто-то оставил USB-накопитель",
            description=(
                "Надпись обещает материалы урока, но происхождение "
                "неизвестно. Настоящие USB-устройства программа не ищет "
                "и не подключает."
            ),
            choices=(
                Choice(
                    id="hand_over",
                    title="Передать учителю или специалисту",
                    hint="Не подключать к рабочему ПК",
                    next_node="safe",
                    event="Учебный накопитель передан специалисту без подключения.",
                    change=StateChange(threat_blocked=True),
                    explanation=(
                        "Проверка неизвестного устройства не должна начинаться с"
                        " подключения к рабочему компьютеру."
                    ),
                ),
                Choice(
                    id="connect",
                    title="Подключить учебный USB",
                    hint="Смоделировать подключение",
                    next_node="connected",
                    event="В модели подключён неизвестный накопитель.",
                    change=StateChange(risk=20, usb_connected=True),
                    explanation=(
                        "Неизвестное устройство оказалось подключено. Это "
                        "создало риск ещё до запуска файлов."
                    ),
                ),
            ),
        ),
        ScenarioNode(
            id="connected",
            title="На накопителе — файл программы",
            description=(
                "Файл «Материалы.exe» выдаёт себя за учебные документы. "
                "Автозапуска нет: решите, что делать дальше."
            ),
            choices=(
                Choice(
                    id="inspect",
                    title="Проверить тип и источник",
                    hint="Не запускать файл при проверке",
                    next_node="checked",
                    event=("Обнаружен исполняемый файл с неподтверждённым происхождением."),
                    change=StateChange(risk=10, source_checked=True),
                    explanation=(
                        "Расширение .exe означает программу. Название "
                        "«Материалы» не превращает её в документ."
                    ),
                ),
                Choice(
                    id="run",
                    title="Запустить учебную программу",
                    hint="Только смоделированный запуск",
                    next_node="running",
                    event=("В модели запущена подозрительная программа с накопителя."),
                    change=StateChange(risk=80, malware_active=True),
                    explanation=(
                        "Запуск дал неизвестной программе возможности учебного "
                        "пользователя; риск резко вырос."
                    ),
                ),
                Choice(
                    id="eject",
                    title="Отключить USB и сообщить",
                    hint="Остановиться без запуска",
                    next_node="safe",
                    event="Учебный накопитель отключён; файл не запускался.",
                    change=StateChange(risk=5, usb_connected=False, threat_blocked=True),
                    explanation=(
                        "Вы остановились до запуска. Подключение всё же следует "
                        "сообщить специалисту."
                    ),
                ),
            ),
        ),
        ScenarioNode(
            id="checked",
            title="Это программа, а не документ",
            description=(
                "Учитель не подтвердил происхождение файла. Проверка не "
                "запускает программу и не гарантирует безопасность "
                "устройства."
            ),
            choices=(
                Choice(
                    id="eject",
                    title="Отключить и передать специалисту",
                    hint="Учесть результат проверки",
                    next_node="safe",
                    event="Накопитель отключён после проверки происхождения.",
                    change=StateChange(risk=0, usb_connected=False, threat_blocked=True),
                    explanation="Вы не дали неизвестной программе выполнить команды.",
                ),
                Choice(
                    id="run",
                    title="Всё же запустить файл",
                    hint="Продолжить учебный эксперимент",
                    next_node="running",
                    event=("Несмотря на проверку запущена учебная подозрительная программа."),
                    change=StateChange(risk=80, malware_active=True),
                    explanation=(
                        "Знание признаков угрозы не защищает, если после "
                        "проверки всё равно разрешить запуск."
                    ),
                ),
            ),
        ),
        ScenarioNode(
            id="running",
            title="Программа продолжает работать",
            description=(
                "Отключить USB недостаточно, если программа уже запущена"
                " на ПК. Выберите дальнейшее действие."
            ),
            choices=(
                Choice(
                    id="isolate",
                    title="Изолировать ПК и сообщить",
                    hint="Остановить активную угрозу в модели",
                    next_node="contained",
                    event=("Учебная сеть и USB отключены, программа остановлена специалистом."),
                    change=StateChange(
                        risk=30,
                        network_connected=False,
                        usb_connected=False,
                        malware_active=False,
                        threat_blocked=True,
                    ),
                    explanation=(
                        "Изоляция остановила дальнейший ущерб. Запуск всё равно "
                        "требует проверки компьютера специалистом."
                    ),
                ),
                Choice(
                    id="ignore",
                    title="Только вытащить накопитель",
                    hint="Не останавливать запущенную программу",
                    next_node="damage",
                    event=(
                        "USB отключён, но работающая программа закрыла доступ к виртуальным файлам."
                    ),
                    change=StateChange(risk=100, usb_connected=False, files_encrypted=True),
                    explanation=(
                        "Программа уже работала в модели ПК. Удаление устройства"
                        " не отменило её запуск."
                    ),
                ),
            ),
        ),
        ScenarioNode(
            id="safe",
            title="Запуск предотвращён",
            description=("Неизвестная программа не выполнялась. Учебные файлы доступны."),
        ),
        ScenarioNode(
            id="contained",
            title="Дальнейший ущерб остановлен",
            description=("Программа остановлена. Учебный ПК остаётся изолированным до проверки."),
        ),
        ScenarioNode(
            id="damage",
            title="USB отключён, программа осталась",
            description=(
                "Доступ потерян только к виртуальным файлам. Реальные USB и файлы не затронуты."
            ),
        ),
    ),
)
