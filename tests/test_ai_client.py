import json

import httpx
import pytest
from openai import OpenAI

from cyberlab.ai_client import DeepSeekClient
from cyberlab.ai_context import build_context
from cyberlab.scenarios import PHISHING
from cyberlab.session import LabSession
from cyberlab.storage import HistoryRepository


@pytest.fixture
def context():
    repository = HistoryRepository(":memory:")
    try:
        lab = LabSession(repository)
        lab.choose("open_link")
        return build_context(PHISHING, lab.entries, lab.active)
    finally:
        repository.close()


def client_with_transport(handler):
    def factory(**options):
        assert options["max_retries"] == 0
        assert options["timeout"] == 12.0
        return OpenAI(http_client=httpx.Client(transport=httpx.MockTransport(handler)), **options)

    return DeepSeekClient(api_key="test-key-not-a-real-secret", sdk_factory=factory)


def test_success_uses_requested_model_non_thinking_budget_and_safe_question(context):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "id": "chat-test",
                "object": "chat.completion",
                "created": 0,
                "model": "deepseek-flash",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "Проверьте адрес сайта."},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 20, "completion_tokens": 8, "total_tokens": 28},
            },
        )

    client = client_with_transport(handler)
    reply = client.answer(
        context, "question", "teacher@example.org пароль: qwerty +7 999 123-45-67 " + "x" * 2000
    )
    assert reply.online and reply.text == "Проверьте адрес сайта."
    assert reply.usage.total == 28
    assert len(requests) == 1
    assert str(requests[0].url) == "https://api.deepseek.com/chat/completions"
    data = json.loads(requests[0].content)
    assert data["model"] == "deepseek-flash"
    assert data["max_tokens"] == 350
    assert data["thinking"] == {"type": "disabled"}
    assert [message["role"] for message in data["messages"]] == ["system", "user"]
    body = data["messages"][1]["content"]
    assert "teacher@example.org" not in body and "qwerty" not in body
    assert "+7 999" not in body and "test-key" not in body
    assert "x" * 1001 not in body
    assert context.payload in body


def test_missing_key_never_constructs_an_sdk_client(context, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    def forbidden(**options):
        pytest.fail("Missing key must not create a network client")

    reply = DeepSeekClient(sdk_factory=forbidden).answer(context, "decision")
    assert not reply.online and reply.text == context.local_decision
    assert "не задан" in reply.error


@pytest.mark.parametrize(
    ("status", "message"),
    [
        (401, "API-ключ"),
        (402, "недостаточно средств"),
        (403, "запретил доступ"),
        (429, "лимит запросов"),
        (500, "недоступен"),
        (404, "не принял запрос"),
    ],
)
def test_api_failures_use_local_explanation_without_retries(context, status, message):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, json={"error": {"message": "SECRET must not be shown"}})

    reply = client_with_transport(handler).answer(context, "analysis")
    assert not reply.online and reply.text == context.local_analysis
    assert message in reply.error
    assert "SECRET" not in reply.error and len(calls) == 1


@pytest.mark.parametrize(
    ("failure", "message"),
    [
        (httpx.ConnectError, "Нет соединения"),
        (httpx.ReadTimeout, "не ответил вовремя"),
    ],
)
def test_network_failure_and_timeout_fall_back(context, failure, message):
    def handler(request):
        raise failure("SECRET", request=request)

    reply = client_with_transport(handler).answer(context, "decision")
    assert not reply.online and reply.text == context.local_decision
    assert message in reply.error and "SECRET" not in reply.error


def test_empty_response_falls_back(context):
    client = client_with_transport(lambda request: httpx.Response(200, json={"choices": []}))
    reply = client.answer(context, "question", "Как проверить ссылку?")
    assert not reply.online and reply.text == context.local_state
