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

    def apply(self, state: ComputerState, event: str) -> ComputerState:
        updates = {key: value for key, value in asdict(self).items() if value is not None}
        return replace(state, **updates, events=(*state.events, event))


@dataclass(frozen=True)
class Choice:
    id: str
    title: str
    hint: str
    next_node: str
    event: str
    change: StateChange = StateChange()


@dataclass(frozen=True)
class ScenarioNode:
    id: str
    title: str
    description: str
    choices: tuple[Choice, ...] = ()

    @property
    def terminal(self) -> bool:
        return not self.choices


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    start_node: str
    nodes: tuple[ScenarioNode, ...]

    def node(self, node_id: str) -> ScenarioNode:
        for node in self.nodes:
            if node.id == node_id:
                return node
        raise ValueError(f"Неизвестный шаг сценария: {node_id}")

    def advance(
        self, node_id: str, state: ComputerState, choice_id: str
    ) -> tuple[ScenarioNode, ComputerState, Choice]:
        for choice in self.node(node_id).choices:
            if choice.id == choice_id:
                return self.node(choice.next_node), choice.change.apply(state, choice.event), choice
        raise ValueError(f"Решение {choice_id!r} недоступно на шаге {node_id!r}.")


@dataclass(frozen=True)
class ComparisonRow:
    label: str
    left: str
    right: str

    @property
    def different(self) -> bool:
        return self.left != self.right


def compare_states(left: ComputerState, right: ComputerState) -> tuple[ComparisonRow, ...]:
    """Те же понятные показатели используются в интерфейсе и автоматических тестах."""

    def values(state: ComputerState) -> tuple[str, ...]:
        return (
            f"{state.risk} / 100",
            "Раскрыты" if state.credentials_exposed else "Защищены",
            "Зашифрованы" if state.files_encrypted else "Доступны",
            "Подключена" if state.network_connected else "Отключена",
            "В карантине" if state.email_quarantined else "Во входящих",
        )

    labels = ("Учебный риск", "Учётные данные", "Файлы", "Сеть", "Письмо")
    return tuple(
        ComparisonRow(label, a, b)
        for label, a, b in zip(labels, values(left), values(right), strict=True)
    )
