"""SQLite хранит дерево снимков, а не одну перезаписываемую историю."""

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from cyberlab.domain import ComputerState


@dataclass(frozen=True)
class HistoryEntry:
    """Снимок конкретного прохождения; parent_id связывает его с предыдущим снимком."""

    id: str
    session_id: str
    parent_id: str | None
    choice_id: str | None
    choice_title: str
    node_id: str
    state: ComputerState
    created_at: str


@dataclass(frozen=True)
class Session:
    id: str
    scenario_id: str
    active_entry_id: str


class HistoryRepository:
    """Читает и записывает историю. Правила сценария остаются в domain.py."""

    def __init__(self, path: str | Path) -> None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(path))
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        try:
            self._initialize()
        except Exception:
            self.connection.close()
            raise

    def _initialize(self) -> None:
        version = self.connection.execute("PRAGMA user_version").fetchone()[0]
        if version > 1:
            raise ValueError("База создана более новой версией CYBERLAB. Обновите приложение.")
        if version == 1:
            return
        self.connection.executescript("""
            BEGIN;
            CREATE TABLE sessions (
                id TEXT PRIMARY KEY,
                scenario_id TEXT NOT NULL,
                active_entry_id TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (id, active_entry_id) REFERENCES entries(session_id, id)
            );
            CREATE TABLE entries (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL REFERENCES sessions(id),
                parent_id TEXT,
                choice_id TEXT,
                choice_title TEXT NOT NULL,
                node_id TEXT NOT NULL,
                state_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE (session_id, id),
                UNIQUE (session_id, parent_id, choice_id),
                FOREIGN KEY (session_id, parent_id) REFERENCES entries(session_id, id),
                CHECK ((parent_id IS NULL) = (choice_id IS NULL))
            );
            CREATE UNIQUE INDEX one_root_per_session
                ON entries(session_id) WHERE parent_id IS NULL;
            CREATE INDEX entries_by_session ON entries(session_id);
            PRAGMA user_version = 1;
            COMMIT;
        """)

    def close(self) -> None:
        self.connection.close()

    def latest_session(self, scenario_id: str) -> Session | None:
        row = self.connection.execute(
            "SELECT * FROM sessions WHERE scenario_id = ? "
            "ORDER BY created_at DESC, rowid DESC LIMIT 1",
            (scenario_id,),
        ).fetchone()
        if row is None:
            return None
        return Session(
            id=row["id"], scenario_id=row["scenario_id"], active_entry_id=row["active_entry_id"]
        )

    def create_session(self, scenario_id: str, start_node: str) -> Session:
        session_id = uuid4().hex
        entry_id = uuid4().hex
        created_at = datetime.now(UTC).isoformat()
        root_entry = HistoryEntry(
            id=entry_id,
            session_id=session_id,
            parent_id=None,
            choice_id=None,
            choice_title="Начало сценария",
            node_id=start_node,
            state=ComputerState(),
            created_at=created_at,
        )
        with self.connection:
            # Сначала создаём сессию без указателя: её первый шаг ещё не записан.
            self.connection.execute(
                "INSERT INTO sessions (id, scenario_id, active_entry_id, created_at) "
                "VALUES (?, ?, NULL, ?)",
                (session_id, scenario_id, created_at),
            )
            self._insert(root_entry)
            self.connection.execute(
                "UPDATE sessions SET active_entry_id = ? WHERE id = ?", (entry_id, session_id)
            )
        return Session(session_id, scenario_id, entry_id)

    def entry(self, entry_id: str, session_id: str) -> HistoryEntry:
        row = self.connection.execute(
            "SELECT * FROM entries WHERE id = ? AND session_id = ?", (entry_id, session_id)
        ).fetchone()
        if row is None:
            raise ValueError("Шаг не найден в текущей сессии.")
        return self._decode(row)

    def entries(self, session_id: str) -> list[HistoryEntry]:
        rows = self.connection.execute(
            "SELECT * FROM entries WHERE session_id = ? ORDER BY rowid", (session_id,)
        ).fetchall()
        return [self._decode(row) for row in rows]

    def activate(self, session_id: str, entry_id: str) -> HistoryEntry:
        """Сохранить выбор шага без изменения самого снимка или его потомков."""
        entry = self.entry(entry_id, session_id)
        with self.connection:
            self.connection.execute(
                "UPDATE sessions SET active_entry_id = ? WHERE id = ?", (entry_id, session_id)
            )
        return entry

    def append(
        self,
        session_id: str,
        parent_id: str,
        choice_id: str,
        choice_title: str,
        node_id: str,
        state: ComputerState,
    ) -> HistoryEntry:
        """Добавить решение к parent_id или открыть уже существующего ребёнка."""
        # with connection объединяет запись снимка и указателя в транзакцию:
        # успешное завершение — commit, исключение — rollback обоих изменений.
        with self.connection:
            # Проверка не даёт добавить решение к шагу из чужой сессии.
            self.entry(parent_id, session_id)
            existing_row = self.connection.execute(
                "SELECT * FROM entries WHERE session_id = ? AND parent_id = ? AND choice_id = ?",
                (session_id, parent_id, choice_id),
            ).fetchone()
            if existing_row is None:
                entry = HistoryEntry(
                    id=uuid4().hex,
                    session_id=session_id,
                    parent_id=parent_id,
                    choice_id=choice_id,
                    choice_title=choice_title,
                    node_id=node_id,
                    state=state,
                    created_at=datetime.now(UTC).isoformat(),
                )
                self._insert(entry)
            else:
                # Тот же выбор из того же шага открывает готовую ветку без дубликата.
                entry = self._decode(existing_row)
            self.connection.execute(
                "UPDATE sessions SET active_entry_id = ? WHERE id = ?", (entry.id, session_id)
            )
        return entry

    def _insert(self, entry: HistoryEntry) -> None:
        self.connection.execute(
            "INSERT INTO entries "
            "(id, session_id, parent_id, choice_id, choice_title, node_id, state_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                entry.id,
                entry.session_id,
                entry.parent_id,
                entry.choice_id,
                entry.choice_title,
                entry.node_id,
                json.dumps(asdict(entry.state), ensure_ascii=False),
                entry.created_at,
            ),
        )

    @staticmethod
    def _decode(row: sqlite3.Row) -> HistoryEntry:
        state_data = json.loads(row["state_json"])
        # JSON хранит массив как список. Для неизменяемого снимка нужен кортеж.
        state_data["events"] = tuple(state_data["events"])
        return HistoryEntry(
            id=row["id"],
            session_id=row["session_id"],
            parent_id=row["parent_id"],
            choice_id=row["choice_id"],
            choice_title=row["choice_title"],
            node_id=row["node_id"],
            state=ComputerState(**state_data),
            created_at=row["created_at"],
        )
