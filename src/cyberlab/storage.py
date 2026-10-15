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
        return Session(row["id"], row["scenario_id"], row["active_entry_id"]) if row else None

    def create_session(self, scenario_id: str, start_node: str) -> Session:
        session_id, entry_id = uuid4().hex, uuid4().hex
        now = datetime.now(UTC).isoformat()
        with self.connection:
            self.connection.execute(
                "INSERT INTO sessions VALUES (?, ?, NULL, ?)", (session_id, scenario_id, now)
            )
            self._insert(
                HistoryEntry(
                    entry_id,
                    session_id,
                    None,
                    None,
                    "Начало сценария",
                    start_node,
                    ComputerState(),
                    now,
                )
            )
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
        # Повтор того же решения открывает уже сохранённую ветку без дубликатов.
        with self.connection:
            self.entry(parent_id, session_id)
            existing = self.connection.execute(
                "SELECT * FROM entries WHERE session_id = ? AND parent_id = ? AND choice_id = ?",
                (session_id, parent_id, choice_id),
            ).fetchone()
            entry = (
                self._decode(existing)
                if existing
                else HistoryEntry(
                    uuid4().hex,
                    session_id,
                    parent_id,
                    choice_id,
                    choice_title,
                    node_id,
                    state,
                    datetime.now(UTC).isoformat(),
                )
            )
            if existing is None:
                self._insert(entry)
            self.connection.execute(
                "UPDATE sessions SET active_entry_id = ? WHERE id = ?", (entry.id, session_id)
            )
        return entry

    def _insert(self, entry: HistoryEntry) -> None:
        self.connection.execute(
            "INSERT INTO entries VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
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
        state = json.loads(row["state_json"])
        state["events"] = tuple(state["events"])
        return HistoryEntry(
            row["id"],
            row["session_id"],
            row["parent_id"],
            row["choice_id"],
            row["choice_title"],
            row["node_id"],
            ComputerState(**state),
            row["created_at"],
        )
