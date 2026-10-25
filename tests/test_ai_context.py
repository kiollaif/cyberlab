import json

from cyberlab.ai_context import MAX_CONTEXT_CHARS, build_context
from cyberlab.scenarios import PHISHING
from cyberlab.session import LabSession
from cyberlab.storage import HistoryRepository


def test_context_has_only_current_path_and_explicitly_requested_comparison():
    repository = HistoryRepository(":memory:")
    try:
        lab = LabSession(repository)
        root = lab.active
        initial = build_context(PHISHING, lab.entries, root)
        assert json.loads(initial.payload)["current"]["decisions"] == []
        lab.choose("open_link")
        lab.choose("submit")
        damage = lab.choose("ignore")
        lab.go_to(root.id)
        safe = lab.choose("report")
        before = lab.entries
        context = build_context(PHISHING, before, safe)
        data = json.loads(context.payload)
        assert len(data["current"]["decisions"]) == 1
        assert data["current"]["computer"]["risk"] == 0
        assert "Продолжить работу" not in context.payload
        assert "Бюджет.txt" not in context.payload
        assert "comparison" not in data
        compared = build_context(PHISHING, before, safe, comparison=(damage, safe))
        pair = json.loads(compared.payload)["comparison"]
        assert [entry["computer"]["risk"] for entry in pair] == [100, 0]
        assert "Продолжить работу" in compared.payload
        assert compared.key != context.key
        assert "риск ниже" in compared.local_comparison
        assert len(compared.payload) <= MAX_CONTEXT_CHARS
        assert lab.entries == before and lab.active == safe
    finally:
        repository.close()


def test_unvisited_outcomes_are_not_serialized():
    repository = HistoryRepository(":memory:")
    try:
        lab = LabSession(repository)
        for choice in (None, "inspect", "open_link", "submit"):
            if choice:
                lab.choose(choice)
            context = build_context(PHISHING, lab.entries, lab.active)
            assert "Атака затронула файлы" not in context.payload
            assert "Атака продолжилась:" not in context.payload
            assert 'files_encrypted": true' not in context.payload
    finally:
        repository.close()
