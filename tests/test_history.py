import sqlite3

import pytest

from cyberlab.session import LabSession
from cyberlab.storage import HistoryRepository


@pytest.fixture
def repository(tmp_path):
    repo = HistoryRepository(tmp_path / "data" / "history.sqlite3")
    yield repo
    repo.close()


def test_rewind_creates_alternative_without_destroying_original(repository):
    lab = LabSession(repository)
    root = lab.active
    lab.choose("open_link")
    compromised = lab.choose("submit")
    damage = lab.choose("ignore")
    assert damage.state.files_encrypted

    lab.go_to(compromised.id)
    assert not lab.active.state.files_encrypted
    isolated = lab.choose("isolate")
    assert isolated.parent_id == damage.parent_id == compromised.id
    assert isolated.state.credentials_exposed
    assert not isolated.state.network_connected
    assert not isolated.state.files_encrypted

    lab.go_to(root.id)
    safe = lab.choose("report")
    assert not safe.state.credentials_exposed
    assert repository.entry(damage.id, lab.session.id) == damage
    assert root.state.risk == 0
    assert len(lab.entries) == 6
    assert lab.session.active_entry_id == safe.id


def test_same_decision_reopens_existing_branch(repository):
    lab = LabSession(repository)
    root = lab.active
    first = lab.choose("inspect")
    lab.go_to(root.id)
    second = lab.choose("inspect")
    assert second == first
    assert len(lab.entries) == 2


def test_restart_restores_active_snapshot_and_all_branches(tmp_path):
    path = tmp_path / "history.sqlite3"
    repo = HistoryRepository(path)
    lab = LabSession(repo)
    root = lab.active
    lab.choose("open_link")
    bad_branch = lab.choose("submit")
    lab.go_to(root.id)
    safe_branch = lab.choose("report")
    expected_entries = lab.entries
    repo.close()

    restored_repo = HistoryRepository(path)
    try:
        restored = LabSession(restored_repo)
        assert restored.active == safe_branch
        assert restored.entries == expected_entries
        restored.go_to(bad_branch.id)
        assert restored.active.state.credentials_exposed
        assert isinstance(restored.active.state.events, tuple)
    finally:
        restored_repo.close()


def test_rewound_selection_is_also_persisted(repository):
    lab = LabSession(repository)
    root = lab.active
    lab.choose("report")
    lab.go_to(root.id)
    assert LabSession(repository).active == root


def test_invalid_choice_leaves_database_unchanged(repository):
    lab = LabSession(repository)
    before = lab.entries
    with pytest.raises(ValueError):
        lab.choose("isolate")
    assert lab.entries == before
    assert LabSession(repository).active == lab.active


def test_failed_active_pointer_update_rolls_back_new_snapshot(repository):
    lab = LabSession(repository)
    root = lab.active
    repository.connection.execute("""
        CREATE TRIGGER reject_save BEFORE UPDATE OF active_entry_id ON sessions
        BEGIN
            SELECT RAISE(ABORT, 'simulated write failure');
        END
    """)
    with pytest.raises(sqlite3.IntegrityError, match="simulated write failure"):
        lab.choose("report")
    assert lab.active == root
    assert lab.entries == [root]
    assert LabSession(repository).active == root


def test_cannot_select_or_append_to_another_session(repository):
    first = LabSession(repository)
    second = repository.create_session("phishing-v1", "inbox")
    with pytest.raises(ValueError, match="текущей сессии"):
        first.go_to(second.active_entry_id)
    with pytest.raises(ValueError, match="текущей сессии"):
        repository.append(
            first.session.id,
            second.active_entry_id,
            "report",
            "Report",
            "reported",
            first.active.state,
        )
    assert len(first.entries) == 1


def test_unknown_schema_version_is_rejected_without_overwriting_data(tmp_path):
    path = tmp_path / "future.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA user_version = 99")
        connection.execute("CREATE TABLE important_data (value TEXT)")
        connection.execute("INSERT INTO important_data VALUES ('keep')")
    with pytest.raises(ValueError, match="более новой"):
        HistoryRepository(path)
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT value FROM important_data").fetchone()[0] == "keep"
