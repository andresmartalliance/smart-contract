"""Bounded retry tests for the actual MAIRA Gemini HTTP client.

No Google requests, secrets, PDFs or quota consumption.
"""
import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException

from app.routers import maira


class FakeGeminiClient:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, url, headers, json):
        self.calls.append((url, headers, json))
        return self.replies.pop(0)


def _http(status, payload=None):
    return httpx.Response(status, json=payload or {"error": {"status": "UNAVAILABLE"}})


def _stub(monkeypatch, replies):
    client = FakeGeminiClient(replies)
    sleep = AsyncMock()
    monkeypatch.setattr(maira.httpx, "AsyncClient", lambda timeout: client)
    monkeypatch.setattr(maira.asyncio, "sleep", sleep)
    return client, sleep


def test_transient_503_is_retried_once_then_succeeds(monkeypatch):
    client, sleep = _stub(monkeypatch, [
        _http(503),
        _http(200, {"candidates": [{"content": {"parts": [{"text": "OK"}]}}]})
    ])
    result = asyncio.run(maira._post_gemini(
        {"contents": [{"parts": [{"text": "synthetic"}]}]},
        "secret-test-only", "gemini-3.6-flash", 110.0))
    assert len(client.calls) == 2
    assert result["candidates"][0]["content"]["parts"][0]["text"] == "OK"
    assert client.calls[0][2] == client.calls[1][2]
    assert client.calls[0][1]["x-goog-api-key"] == "secret-test-only"
    sleep.assert_awaited_once_with(2)


def test_persistent_503_fails_after_exactly_two_attempts(monkeypatch):
    client, sleep = _stub(monkeypatch, [_http(503), _http(503)])
    with pytest.raises(HTTPException) as error:
        asyncio.run(maira._post_gemini({"contents": []}, "secret", "gemini-3.6-flash", 110.0))
    assert error.value.status_code == 502
    assert "después de un reintento" in error.value.detail
    assert "secret" not in error.value.detail
    assert len(client.calls) == 2
    sleep.assert_awaited_once_with(2)


def test_non_transient_400_is_not_retried(monkeypatch):
    client, sleep = _stub(monkeypatch, [_http(400, {"error": {"status": "INVALID_ARGUMENT", "message": "request error"}})])
    with pytest.raises(HTTPException) as error:
        asyncio.run(maira._post_gemini({"contents": []}, "secret", "gemini-3.6-flash", 110.0))
    assert error.value.status_code == 502
    assert len(client.calls) == 1
    sleep.assert_not_awaited()


def test_429_does_not_retry_or_multiply_quota_requests(monkeypatch):
    client, sleep = _stub(monkeypatch, [_http(429, {"error": {"status": "RESOURCE_EXHAUSTED"}})])
    with pytest.raises(HTTPException) as error:
        asyncio.run(maira._post_gemini({"contents": []}, "secret", "gemini-3.6-flash", 110.0))
    assert error.value.status_code == 502
    assert "cuota" in error.value.detail
    assert len(client.calls) == 1
    sleep.assert_not_awaited()
