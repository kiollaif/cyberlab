"""Чистая модель симуляции: никаких Qt, SQL, сети или действий с файлами ОС."""

from dataclasses import asdict, dataclass, replace


@dataclass(frozen=True)
class VirtualFile:
    name: str
    content: str


VIRTUAL_FILES = (
    VirtualFile("Бюджет.txt", "Учебный бюджет проекта\nОборудование: 45 000 ₽\nОбучение: 15 000 ₽"),
    VirtualFile("План проекта.txt", "План CYBERLAB\n1. Проверить почту\n2. Подготовить отчёт"),
)


@dataclass(frozen=True)
class ComputerState:
    """Неизменяемый снимок. Старые ветки не меняются при новых решениях."""

    risk: int = 0
    credentials_exposed: bool = False
    network_connected: bool = True
    files_encrypted: bool = False
    email_quarantined: bool = False
    email_inspected: bool = False
    browser_open: bool = False
    events: tuple[str, ...] = ("Получено подозрительное письмо от службы поддержки.",)
    attachment_opened: bool = False
    macros_enabled: bool = False
    usb_connected: bool = False
    malware_active: bool = False
    source_verified: bool = False
    threat_blocked: bool = False

    def __post_init__(self) -> None:
        if not 0 <= self.risk <= 100:
            raise ValueError("Риск должен быть от 0 до 100.")


@dataclass(frozen=True)
class StateChange:
    """Изменения только перечисленных показателей; None сохраняет старое значение."""

    risk: int | None = None
    credentials_exposed: bool | None = None
    network_connected: bool | None = None
    files_encrypted: bool | None = None
    email_quarantined: bool | None = None
    email_inspected: bool | None = None
    browser_open: bool | None = None
    attachment_opened: bool | None = None
    macros_enabled: bool | None = None
    usb_connected: bool | None = None
    malware_active: bool | None = None
    source_verified: bool | None = None
    threat_blocked: bool | None = None

    def apply(self, state: ComputerState, event: str) -> ComputerState:
        """Создать новый снимок с изменениями и дополнительной записью журнала."""
        updated_values = {}
        for field_name, new_value in asdict(self).items():
            # False и 0 тоже являются изменениями. Пропускаем только None.
            if new_value is not None:
                updated_values[field_name] = new_value

        new_events = state.events + (event,)
        # replace создаёт копию dataclass: исходный снимок старой ветки остаётся прежним.
        return replace(state, **updated_values, events=new_events)


@dataclass(frozen=True)
class Choice:
    """Один вариант решения: куда перейти и какие показатели изменить."""

    id: str
    title: str
    hint: str
    next_node: str
    event: str
    change: StateChange = StateChange()
    explanation: str = ""


@dataclass(frozen=True)
class ScenarioNode:
    """Ситуация сценария. Пустой choices означает завершение ветки."""

    id: str
    title: str
    description: str
    choices: tuple[Choice, ...] = ()

    @property
    def terminal(self) -> bool:
        return not self.choices


@dataclass(frozen=True)
class Scenario:
    """Заранее описанные ситуации и переходы между ними, без истории прохождения."""

    id: str
    title: str
    start_node: str
    nodes: tuple[ScenarioNode, ...]
    kind: str = "phishing"
    summary: str = "Срочное письмо и чужая ссылка: проверьте источник перед отправкой данных."
    initial_event: str = "Получено подозрительное письмо от службы поддержки."
    mail_subject: str = "Срочно подтвердите пароль"
    mail_body: str = "Ваш пароль истекает через 15 минут. Подтвердите учётную запись."
    sender_address: str = "help@cyberlab-support.invalid"
    site_address: str = "https://login.cyberlab-check.invalid"
    artifact: str = ""

    def node(self, node_id: str) -> ScenarioNode:
        for node in self.nodes:
            if node.id == node_id:
                return node
        raise ValueError(f"Неизвестный шаг сценария: {node_id}")

    def advance(
        self, node_id: str, state: ComputerState, choice_id: str
    ) -> tuple[ScenarioNode, ComputerState, Choice]:
        """Найти доступное решение и вычислить следующий шаг и состояние ПК."""
        current_node = self.node(node_id)
        for choice in current_node.choices:
            if choice.id == choice_id:
                next_node = self.node(choice.next_node)
                next_state = choice.change.apply(state, choice.event)
                return next_node, next_state, choice
        raise ValueError(f"Решение {choice_id!r} недоступно на шаге {node_id!r}.")


@dataclass(frozen=True)
class ComparisonRow:
    label: str
    left: str
    right: str

    @property
    def different(self) -> bool:
        return self.left != self.right


def compare_states(
    left: ComputerState, right: ComputerState, scenario: Scenario | None = None
) -> tuple[ComparisonRow, ...]:
    """Те же понятные показатели используются в интерфейсе и автоматических тестах."""

    def display_values(state: ComputerState) -> tuple[str, ...]:
        return (
            f"{state.risk} / 100",
            "Раскрыты" if state.credentials_exposed else "Защищены",
            "Зашифрованы" if state.files_encrypted else "Доступны",
            "Подключена" if state.network_connected else "Отключена",
            (
                "Активна"
                if state.malware_active
                else "Остановлена"
                if state.threat_blocked
                else "Запуск не зафиксирован"
            )
            if scenario is not None and scenario.kind != "phishing"
            else ("В карантине" if state.email_quarantined else "Во входящих"),
        )

    labels = ("Учебный риск", "Учётные данные", "Файлы", "Сеть", "Письмо")
    if scenario is not None and scenario.kind != "phishing":
        labels = (*labels[:4], "Учебная угроза")
    comparison_rows = []
    # zip берёт по одному элементу из каждого набора в одинаковом порядке.
    for label, left_value, right_value in zip(
        labels, display_values(left), display_values(right), strict=True
    ):
        comparison_rows.append(ComparisonRow(label, left_value, right_value))
    return tuple(comparison_rows)
