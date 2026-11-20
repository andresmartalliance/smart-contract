"""Diagnostic cannot expose secrets and distinguishes authentication vs inference."""
import asyncio
import logging

import httpx

from app.gemini_deploy_probe import run_gemini_deploy_probe, MODEL


def test_model_lookup_200_generation_503_is_provider_generation_failure(monkeypatch, caplog):
    async def handler(request):
        assert request.headers["x-goog-api-key"] == "fake-confidential-key"
        if request.method == "GET":
            return httpx.Response(200, json={"name": "models/" + MODEL})
        assert request.method == "POST"
        return httpx.Response(503, json={"error": {"status": "UNAVAILABLE",
            "message": "private provider message must not leak"}})
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client)
    with caplog.at_level(logging.WARNING):
        answer = asyncio.run(run_gemini_deploy_probe("fake-confidential-key"))
    assert [x["phase"] for x in answer] == ["model_get", "generation"]
    assert [x["http"] for x in answer] == [200, 503]
    assert [x["state"] for x in answer] == ["OK", "UNAVAILABLE"]
    assert "fake-confidential-key" not in caplog.text
    assert "private provider message" not in caplog.text


def test_invalid_key_does_not_call_generation(monkeypatch):
    calls = []
    def handler(request):
        calls.append(request.method)
        return httpx.Response(403, json={"error": {"status": "PERMISSION_DENIED"}})
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client)
    answer = asyncio.run(run_gemini_deploy_probe("invalid-key"))
    assert calls == ["GET"]
    assert len(answer) == 1
    assert answer[0]["state"] == "PERMISSION_DENIED"
