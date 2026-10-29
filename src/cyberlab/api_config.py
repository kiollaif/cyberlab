"""Настройки поставщика без секретов. Значение ключа читается отдельно из окружения."""

import os
import re
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class ProviderConfig:
    provider: str = "deepseek"
    label: str = "DeepSeek AI"
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-flash"
    key_env: str = "DEEPSEEK_API_KEY"

    @classmethod
    def from_environment(cls):
        provider = os.environ.get("CYBERLAB_AI_PROVIDER", "deepseek").strip().lower()
        if provider == "local":
            return cls(provider="local", label="Локальный наставник")
        if provider == "deepseek":
            return cls()
        if provider != "custom":
            raise ValueError(
                "Неизвестный CYBERLAB_AI_PROVIDER. Выберите local, deepseek или custom."
            )
        address = os.environ.get("CYBERLAB_AI_BASE_URL", "").strip()
        model = os.environ.get("CYBERLAB_AI_MODEL", "").strip()
        key_env = os.environ.get("CYBERLAB_AI_KEY_ENV", "CYBERLAB_AI_API_KEY").strip()
        try:
            url = urlsplit(address)
            _ = url.port  # Проверяем также некорректный номер порта до создания SDK.
        except ValueError:
            raise ValueError("Проверьте формат CYBERLAB_AI_BASE_URL и номер порта.") from None
        loopback = url.hostname in ("localhost", "127.0.0.1", "::1")
        if (
            not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
            or not (url.scheme == "https" or (url.scheme == "http" and loopback))
        ):
            raise ValueError(
                "Для API нужен HTTPS-адрес без ключа в URL; HTTP разрешён только локально."
            )
        if not model or len(model) > 120 or any(c.isspace() for c in model):
            raise ValueError("Задайте CYBERLAB_AI_MODEL: имя модели без пробелов, до 120 символов.")
        if not re.fullmatch(r"[A-Z_][A-Z0-9_]{0,79}", key_env):
            raise ValueError("CYBERLAB_AI_KEY_ENV должен содержать имя переменной, а не сам ключ.")
        return cls("custom", "API-наставник", address.rstrip("/"), model, key_env)
