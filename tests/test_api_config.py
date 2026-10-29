"""Поставщик настраивается без реальных ключей и платных запросов."""

import json

import httpx
import pytest
from openai import OpenAI

from cyberlab.ai_client import DeepSeekClient
from cyberlab.ai_context import build_context
from cyberlab.api_config import ProviderConfig
from cyberlab.scenarios import SCENARIOS
from cyberlab.session import LabSession
from cyberlab.storage import HistoryRepository


@pytest.fixture
def context():
    repository = HistoryRepository(":memory:")
    try:
        lab = LabSession(repository, SCENARIOS[3])
        lab.choose("connect")
        return build_context(lab.scenario, lab.entries, lab.active)
    finally:
        repository.close()


def test_custom_api_uses_configured_model_and_no_deepseek_extension(monkeypatch, context):
    monkeypatch.setenv("CYBERLAB_AI_PROVIDER", "custom")
    monkeypatch.setenv("CYBERLAB_AI_BASE_URL", "https://mentor.example/v1")
    monkeypatch.setenv("CYBERLAB_AI_MODEL", "school-model")
    monkeypatch.setenv("CYBERLAB_AI_API_KEY", "test-key")
    captured = []

    def handler(request):
        captured.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "Проверьте источник."}}]
            },
        )

    def factory(**options):
        assert options["timeout"] == 12 and options["max_retries"] == 0
        return OpenAI(http_client=httpx.Client(transport=httpx.MockTransport(handler)), **options)

    client = DeepSeekClient(sdk_factory=factory)
    reply = client.answer(context, "question", "password: real-secret teacher@example.org")
    assert reply.online and client.display_name == "API-наставник"
    assert str(captured[0].url) == "https://mentor.example/v1/chat/completions"
    data = json.loads(captured[0].content)
    assert data["model"] == "school-model" and data["max_tokens"] == 350
    assert "thinking" not in data
    assert "real-secret" not in str(data) and "teacher@example.org" not in str(data)
    assert "test-key" not in str(data)
    assert "USB" in context.local_state and "Проверьте адрес отправителя" not in context.local_state
    # Будущее событие и файлы не передаются модели.
    assert "работающая программа закрыла доступ" not in context.payload
    assert "Бюджет.txt" not in context.payload


@pytest.mark.parametrize(
    "address",
    [
        "http://remote.example/v1",
        "https://user:password@mentor.example/v1",
        "https://mentor.example/v1?api_key=secret",
        "file:///tmp/private",
        "https://mentor.example/#secret",
    ],
)
def test_invalid_configuration_falls_back_without_sdk(monkeypatch, context, address):
    monkeypatch.setenv("CYBERLAB_AI_PROVIDER", "custom")
    monkeypatch.setenv("CYBERLAB_AI_BASE_URL", address)
    monkeypatch.setenv("CYBERLAB_AI_MODEL", "model")

    def forbidden(**kwargs):
        pytest.fail("invalid configuration must never make a request")

    client = DeepSeekClient(api_key="test", sdk_factory=forbidden)
    reply = client.answer(context, "decision")
    assert not reply.online and reply.text == context.local_decision
    assert reply.error and "secret" not in reply.error and "password" not in reply.error


def test_local_provider_ignores_existing_api_key_and_answers_by_rules(monkeypatch, context):
    monkeypatch.setenv("CYBERLAB_AI_PROVIDER", "local")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "never-send-this")
    client = DeepSeekClient()
    assert not client.configured
    reply = client.answer(context, "question", "Что делать с чужим USB?")
    assert not reply.online
    assert "передайте специалисту" in reply.text
    assert context.local_state in reply.text


def test_loopback_endpoint_and_invalid_model_or_key_name(monkeypatch):
    monkeypatch.setenv("CYBERLAB_AI_PROVIDER", "custom")
    monkeypatch.setenv("CYBERLAB_AI_BASE_URL", "http://127.0.0.1:8000/v1")
    monkeypatch.setenv("CYBERLAB_AI_MODEL", "local-model")
    assert ProviderConfig.from_environment().base_url.startswith("http://127.0.0.1")
    monkeypatch.setenv("CYBERLAB_AI_KEY_ENV", "sk-real-secret")
    with pytest.raises(ValueError):
        ProviderConfig.from_environment()
