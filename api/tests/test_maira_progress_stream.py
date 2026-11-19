"""Authenticated NDJSON streaming reports actual milestones and terminal errors."""
import json

from app.main import app
from app.routers import maira
from tests.test_maira_import import valid_proposal


def test_stream_requires_google(testing, monkeypatch):
    client, _ = testing
    monkeypatch.delenv("SMART_GOOGLE_CLIENT_ID", raising=False)
    response = client.post("/api/v1/maira/workflow-import/stream",
                           files={"file": ("test.pdf", b"%PDF-1.4 synthetic", "application/pdf")})
    assert response.status_code == 503


def test_stream_real_callback_sequence(testing, monkeypatch):
    client, _ = testing
    monkeypatch.setenv("SMART_GEMINI_API_KEY", "fake")
    app.dependency_overrides[maira._verify_identity] = lambda: "authorized@example.com"

    async def synthetic(data, suffix, name, key, kind=None, progress=None):
        assert progress is not None
        await progress("PREPARACION", "Preparando la lectura del documento.")
        await progress("GEMINI", "Gemini está interpretando las actividades.")
        await progress("COMPILACION", "Gemini respondió. Verificando actividades y dependencias.")
        return maira._parse_proposal(valid_proposal())

    monkeypatch.setattr(maira, "_call_gemini", synthetic)
    try:
        resp = client.post("/api/v1/maira/workflow-import/stream",
                           files={"file": ("test.pdf", b"%PDF-1.4 synthetic", "application/pdf")},
                           data={"party_kind": "JURIDICA"})
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/x-ndjson")
        messages = [json.loads(line) for line in resp.text.splitlines()]
        assert [e["phase"] for e in messages if e["event"] == "progress"] == [
            "VALIDADO", "PREPARACION", "GEMINI", "COMPILACION", "FINALIZANDO"
        ]
        assert messages[-1]["event"] == "done"
        assert messages[-1]["result"]["mapped_steps"] == 1
        assert messages[-1]["result"]["status"] == "DRAFT_FOR_HUMAN_REVIEW"
    finally:
        app.dependency_overrides.pop(maira._verify_identity, None)


def test_stream_error_stops_without_false_completion(testing, monkeypatch):
    client, _ = testing
    monkeypatch.setenv("SMART_GEMINI_API_KEY", "fake")
    app.dependency_overrides[maira._verify_identity] = lambda: "authorized@example.com"
    async def synthetic_error(data, suffix, name, key, kind=None, progress=None):
        await progress("GEMINI", "Gemini está interpretando las actividades.")
        raise maira.HTTPException(504, "Gemini agotó el tiempo de análisis.")

    monkeypatch.setattr(maira, "_call_gemini", synthetic_error)
    try:
        resp = client.post("/api/v1/maira/workflow-import/stream",
                           files={"file": ("test.pdf", b"%PDF-1.4 synthetic", "application/pdf")})
        events = [json.loads(line) for line in resp.text.splitlines()]
        assert events[-1]["event"] == "error"
        assert "tiempo" in events[-1]["message"]
        assert not any(e["event"] == "done" for e in events)
    finally:
        app.dependency_overrides.pop(maira._verify_identity, None)
