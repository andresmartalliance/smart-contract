"""Tiny probes: never log credentials or user data, maximum two generations."""
import asyncio
import logging
import httpx
from app.gemini_deploy_probe import run_gemini_deploy_probe, MODELS


def test_fallback_candidate_succeeds_without_exposing_key(monkeypatch, caplog):
    calls = []
    async def handler(request):
        assert request.headers["x-goog-api-key"] == "private-mock-key"
        calls.append((request.method, str(request.url)))
        if request.method == "GET":
            return httpx.Response(200, json={"name": "models/test"})
        if MODELS[0] in str(request.url):
            return httpx.Response(503, json={"error": {"status": "UNAVAILABLE",
                 "message": "sensitive-provider-body"}})
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "OK"}]}}]})
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client)
    with caplog.at_level(logging.WARNING):
        result = asyncio.run(run_gemini_deploy_probe("private-mock-key"))
    assert len(result) == 4
    assert result[-1]["state"] == "OK_TEXT"
    assert result[-1]["model"] == MODELS[1]
    assert sum(m == "POST" for m, _ in calls) == 2
    assert "private-mock-key" not in caplog.text
    assert "sensitive-provider-body" not in caplog.text


def test_auth_denied_does_not_generate(monkeypatch):
    calls = []
    def handler(request):
        calls.append(request.method)
        return httpx.Response(403, json={"error": {"status": "PERMISSION_DENIED"}})
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client)
    result = asyncio.run(run_gemini_deploy_probe("invalid"))
    assert len(result) == 2
    assert all(r["state"] == "PERMISSION_DENIED" for r in result)
    assert calls == ["GET", "GET"]
