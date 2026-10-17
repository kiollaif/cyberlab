"""Совместимость с базой, созданной кодом до изменения интерфейса."""

import sqlite3
from pathlib import Path

from cyberlab.session import LabSession
from cyberlab.storage import HistoryRepository


def test_old_database_preserves_all_snapshots_and_can_branch(tmp_path):
    database = tmp_path / "old.sqlite3"
    fixture = Path(__file__).parent / "fixtures" / "history_v1.sql"
    with sqlite3.connect(database) as connection:
        connection.executescript(fixture.read_text(encoding="utf-8"))
        original_entries = connection.execute("SELECT * FROM entries ORDER BY rowid").fetchall()
        original_sessions = connection.execute("SELECT * FROM sessions").fetchall()
        original_schema = connection.execute(
            "SELECT sql FROM sqlite_master ORDER BY name"
        ).fetchall()

    repository = HistoryRepository(database)
    try:
        lab = LabSession(repository)
        assert len(lab.entries) == 14
        assert lab.active.id == original_sessions[0][2]
        assert lab.active.state.files_encrypted
        assert tuple(repository.connection.execute("PRAGMA user_version").fetchone()) == (1,)
        assert [
            tuple(row)
            for row in repository.connection.execute("SELECT * FROM entries ORDER BY rowid")
        ] == original_entries
        assert [
            tuple(row)
            for row in repository.connection.execute("SELECT sql FROM sqlite_master ORDER BY name")
        ] == original_schema
        root = lab.entries[0]
        lab.go_to(root.id)
        safe = lab.choose("report")
        assert not safe.state.credentials_exposed
        assert len(lab.entries) == 14  # старый выбор повторно открывается без дубликата
        assert [
            tuple(row)
            for row in repository.connection.execute("SELECT * FROM entries ORDER BY rowid")
        ] == original_entries
    finally:
        repository.close()

    reopened = HistoryRepository(database)
    try:
        assert LabSession(reopened).active == safe
    finally:
        reopened.close()
