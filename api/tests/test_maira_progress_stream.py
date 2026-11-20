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


def test_diagnose_models_requires_google_auth(testing, monkeypatch):
    client, _ = testing
    monkeypatch.delenv("SMART_GOOGLE_CLIENT_ID", raising=False)
    assert client.post("/api/v1/maira/workflow-import/diagnose-models").status_code == 503


def test_diagnose_models_finds_real_text_alternative_without_documents(testing, monkeypatch):
    from app.routers import maira
    client, _ = testing
    monkeypatch.setenv("SMART_GEMINI_API_KEY", "secret_test_key")
    monkeypatch.setenv("SMART_GEMINI_MODEL", "gemini-3.6-flash")
    app.dependency_overrides[maira._verify_identity] = lambda: "authorized@example.com"
    captured = []

    async def fake_probe(key, model):
        captured.append(model)
        assert key == "secret_test_key"
        return {"model": model, "state": "OK" if model == "gemini-3.5-flash-lite" else "UNAVAILABLE",
                "http": 200 if model == "gemini-3.5-flash-lite" else 503}

    monkeypatch.setattr(maira, "_probe_gemini_model", fake_probe)
    try:
        response = client.post("/api/v1/maira/workflow-import/diagnose-models")
        assert response.status_code == 200
        assert sorted(captured) == ["gemini-3.5-flash-lite", "gemini-3.6-flash"]
        assert response.json()["recommended_model"] == "gemini-3.5-flash-lite"
        assert "secret_test_key" not in response.text
        assert "PDF" in response.json()["notice"]
    finally:
        app.dependency_overrides.pop(maira._verify_identity, None)


def test_stream_override_is_limited_to_approved_flash_name(testing, monkeypatch):
    client, _ = testing
    monkeypatch.setenv("SMART_GEMINI_API_KEY", "fake")
    app.dependency_overrides[maira._verify_identity] = lambda: "authorized@example.com"
    captured = {}

    async def synthetic(data, suffix, name, key, kind=None, progress=None, model_override=None):
        captured["model"] = model_override
        await progress("GEMINI", "Lectura")
        return maira._parse_proposal(valid_proposal())

    monkeypatch.setattr(maira, "_call_gemini", synthetic)
    try:
        files = {"file": ("diagram.pdf", b"%PDF-1.4 synthetic", "application/pdf")}
        valid = client.post("/api/v1/maira/workflow-import/stream", files=files,
                            data={"model_choice": "gemini-3.5-flash-lite"})
        assert valid.status_code == 200
        assert captured["model"] == "gemini-3.5-flash-lite"
        invalid = client.post("/api/v1/maira/workflow-import/stream", files=files,
                              data={"model_choice": "unverified-expensive-pro"})
        assert invalid.status_code == 422
    finally:
        app.dependency_overrides.pop(maira._verify_identity, None)


def test_diagnose_reports_both_models_unavailable_without_recommending(testing, monkeypatch):
    client, _ = testing
    monkeypatch.setenv("SMART_GEMINI_API_KEY", "fake")
    app.dependency_overrides[maira._verify_identity] = lambda: "authorized@example.com"

    async def unavailable(key, model):
        return {"model": model, "state": "UNAVAILABLE", "http": 503}

    monkeypatch.setattr(maira, "_probe_gemini_model", unavailable)
    try:
        response = client.post("/api/v1/maira/workflow-import/diagnose-models")
        assert response.status_code == 200
        assert response.json()["verified"] is False
        assert response.json()["recommended_model"] is None
    finally:
        app.dependency_overrides.pop(maira._verify_identity, None)

def test_diagnose_configured_flash_lite_is_verified_without_other_model(testing, monkeypatch):
    client, _ = testing
    monkeypatch.setenv("SMART_GEMINI_API_KEY", "fake")
    monkeypatch.setenv("SMART_GEMINI_MODEL", "gemini-3.5-flash-lite")
    app.dependency_overrides[maira._verify_identity] = lambda: "authorized@example.com"
    called = []
    async def fake_probe(key, model):
        called.append(model)
        return {"model": model, "state": "OK", "http": 200}
    monkeypatch.setattr(maira, "_probe_gemini_model", fake_probe)
    try:
        response = client.post("/api/v1/maira/workflow-import/diagnose-models")
        assert response.status_code == 200
        assert called == ["gemini-3.5-flash-lite"]
        assert response.json()["recommended_model"] == "gemini-3.5-flash-lite"
    finally:
        app.dependency_overrides.pop(maira._verify_identity, None)
