"""Tests con cliente simulado (mock) para retry, DailyLimitError y caché."""
import pytest
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.triage import call_api_with_retry, DailyLimitError
from evals.run_evals import get_cache_path, load_cached_result, save_cached_result


class FakeResponse:
    def __init__(self, status_code, headers=None, body=None):
        self.status_code = status_code
        self.headers = headers or {}
        self._body = body or {}
        # Simular request para que openai.RateLimitError funcione
        class FakeRequest:
            pass
        self.request = FakeRequest()

    def json(self):
        return self._body


def make_exc(status_code, headers=None, body_dict=None):
    # Usar openai.RateLimitError o openai.AuthenticationError etc.
    import openai
    resp = FakeResponse(status_code, headers=headers or {}, body=body_dict or {})
    if status_code == 429:
        msg = (body_dict.get("message", "") if body_dict else "")
        exc = openai.RateLimitError(msg, response=resp, body=body_dict or {})
    elif status_code == 401:
        msg = (body_dict.get("message", "") if body_dict else "")
        exc = openai.AuthenticationError(msg, response=resp, body=body_dict or {})
    elif status_code >= 500:
        msg = (body_dict.get("message", "") if body_dict else "")
        exc = openai.InternalServerError(msg, response=resp, body=body_dict or {})
    else:
        exc = Exception("generic")
        exc.status_code = status_code
        exc.response = resp
        exc.body = body_dict or {}
    return exc


def test_retry_transient_429():
    import openai
    client = MagicMock(spec=["chat", "completions", "create"])
    exc = make_exc(429, headers={"retry-after": "0"}, body_dict={"message": "rate limit per minute"})
    client.chat.completions.create.side_effect = [exc, MagicMock()]
    result = call_api_with_retry(client, "test-model", [{"role": "user", "content": "hello"}], [])
    assert client.chat.completions.create.call_count == 2


def test_retry_401_not_retried():
    import openai
    client = MagicMock()
    exc = make_exc(401, headers={}, body_dict={"message": "unauthorized"})
    client.chat.completions.create.side_effect = exc
    with pytest.raises(openai.AuthenticationError):
        call_api_with_retry(client, "m", [{"role": "user"}], [])
    assert client.chat.completions.create.call_count == 1


def test_retry_429_daily_limit_raises_daily_limit_error():
    import openai
    client = MagicMock()
    exc = make_exc(
        429,
        headers={"retry-after": "10", "x-ratelimit-reset": "1759257600000"},
        body_dict={"message": "free-models-per-day exceeded", "metadata": {"limit_source": "openrouter_free_tier_daily"}},
    )
    client.chat.completions.create.side_effect = exc
    with pytest.raises(DailyLimitError) as exc_info:
        call_api_with_retry(client, "m", [{"role": "user"}], [])
    assert exc_info.value.reset_time_local != ""


def test_cache_reused():
    # Probar reutilización de caché sin llamar a OpenRouter
    with patch("os.environ.get", return_value="openrouter/free"):
        # Escribir caché manualmente
        cache_path = get_cache_path("test_case", "openrouter/free")
        save_cached_result(cache_path, {"triage_output": {"results": [{"test_name": "t", "category": "BUG_REAL"}]}, "trace_info": {"total_time": 0.1}})
        data = load_cached_result(cache_path)
        assert data is not None
        assert data["triage_output"]["results"][0]["category"] == "BUG_REAL"
        # Limpiar
        if cache_path.exists():
            cache_path.unlink()


def test_daily_limit_stops_evals():
    # Simular que DailyLimitError detiene la evaluación
    # No requiere llamada real a OpenRouter; solo verificar que la excepción se lanza
    import openai
    client = MagicMock()
    exc = make_exc(
        429,
        headers={"x-ratelimit-reset": "1759257600000"},
        body_dict={"message": "free-models-per-day exceeded", "metadata": {"limit_source": "openrouter_free_tier_daily"}},
    )
    client.chat.completions.create.side_effect = exc
    with pytest.raises(DailyLimitError) as exc_info:
        call_api_with_retry(client, "m", [{"role": "user"}], [])
    assert "Reinicio" in str(exc_info.value)
