import pytest

from cyberlab.assessment import assess_path
from cyberlab.learning import risk_level
from cyberlab.scenarios import PHISHING
from cyberlab.session import LabSession
from cyberlab.statistics import load_results
from cyberlab.storage import HistoryRepository


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, "Низкий"),
        (25, "Низкий"),
        (26, "Умеренный"),
        (50, "Умеренный"),
        (51, "Высокий"),
        (75, "Высокий"),
        (76, "Критический"),
        (100, "Критический"),
    ],
)
def test_risk_band_boundaries(value, expected):
    assert risk_level(value) == expected


def test_assessment_counts_actual_decisions_and_preserves_old_result(tmp_path):
    path = tmp_path / "history.sqlite3"
    repo = HistoryRepository(path)
    lab = LabSession(repo)
    root = lab.active.id
    assert assess_path(PHISHING, lab.entries, lab.active).score is None
    for action in ("open_link", "submit", "ignore"):
        lab.choose(action)
    damaged = lab.active
    result = assess_path(PHISHING, lab.entries, damaged)
    assert (result.safe, result.risky, result.neutral, result.score) == (0, 3, 0, 0)
    assert result.risks == (0, 30, 75, 100)
    assert len(result.mistakes) == 3 and all(item.recommendation for item in result.mistakes)
    lab.go_to(root)
    safe = lab.choose("report")
    assert assess_path(PHISHING, lab.entries, safe).score == 100
    assert assess_path(PHISHING, lab.entries, damaged) == result
    lab.go_to(root)
    assert {item.entry_id for item in load_results(repo, (PHISHING,))} == {damaged.id, safe.id}
    repo.close()
    reopened = HistoryRepository(path)
    try:
        assert {item.score for item in load_results(reopened, (PHISHING,))} == {0, 100}
        assert reopened.connection.execute("PRAGMA user_version").fetchone()[0] == 1
    finally:
        reopened.close()
