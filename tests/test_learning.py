import pytest

from cyberlab.learning import decision_rating, history_path, remaining_decisions, state_summary
from cyberlab.mentor import explain_decision, explain_state
from cyberlab.scenarios import PHISHING
from cyberlab.session import LabSession
from cyberlab.storage import HistoryRepository


def test_review_uses_only_ancestors_and_keeps_old_sessions(tmp_path):
    repository = HistoryRepository(tmp_path / "learning.sqlite3")
    try:
        lab = LabSession(repository)
        first_session = lab.session
        root = lab.active
        opened = lab.choose("open_link")
        submitted = lab.choose("submit")
        damage = lab.choose("ignore")
        lab.go_to(root.id)
        safe = lab.choose("report")
        assert history_path(lab.entries, damage.id) == [root, opened, submitted, damage]
        assert history_path(lab.entries, safe.id) == [root, safe]
        before = lab.entries
        lab.new_session()
        second_session = lab.session
        lab.open_session(first_session.id)
        assert lab.active == safe
        assert lab.entries == before
        assert len(repository.sessions(PHISHING.id)) == 2
        lab.open_session(second_session.id)
        assert len(lab.entries) == 1
        with pytest.raises(ValueError):
            lab.open_session("missing")
        assert lab.session == second_session
    finally:
        repository.close()


def test_progress_counts_longest_remaining_route():
    assert remaining_decisions(PHISHING, "inbox") == 4
    assert remaining_decisions(PHISHING, "fake_site") == 2
    assert remaining_decisions(PHISHING, "reported") == 0


def test_feedback_describes_actual_changes_without_future_events():
    with_memory = HistoryRepository(":memory:")
    try:
        lab = LabSession(with_memory)
        root = lab.active
        assert "зашифрован" not in explain_state(root.state)
        inspected = lab.choose("inspect")
        explanation = explain_decision("inspect", root.state, inspected.state)
        assert "cyberlab.example" in explanation
        assert "зашифрован" not in explanation
        assert decision_rating(root.state, inspected.state) == "Полезное решение"
        opened = lab.choose("open_link")
        assert decision_rating(inspected.state, opened.state) == "Риск вырос"
        submitted = lab.choose("submit")
        isolated = lab.choose("isolate")
        assert decision_rating(submitted.state, isolated.state) == "Полезное решение"
        assert "остался раскрытым" in explain_decision("isolate", submitted.state, isolated.state)
        assert "пароль раскрыт" in state_summary(isolated.state)
    finally:
        with_memory.close()
