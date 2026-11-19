import os
import pytest
from fastapi import HTTPException
from app.routers.maira import _parse_proposal, _validate_file, import_status


def valid_proposal():
    return {"workflow": {
        "key":"TEST_V2","name":"Proceso","modality_key":None,
        "nodes":[
          {"id":"i","kind":"START","label":"Inicio","policy":"ORG_REQUIRED"},
          {"id":"uno","kind":"NOTIFICATION","label":"Correo de carga","role":"SISTEMA","config":{"source_step":"2.1"}},
          {"id":"f","kind":"END","label":"Fin","policy":"ORG_REQUIRED"},
        ],"edges":[{"source":"i","target":"uno"},{"source":"uno","target":"f"}]},
        "source_map":[{"source_step":"2.1","node_id":"uno","source_excerpt":"CORREO CON DOCUMENTOS","page":1,"confidence":"alta"}],
        "questions":[],"observations":[]}


def test_ready_requires_google_allowlist_and_key(monkeypatch):
    for name in ("SMART_GOOGLE_CLIENT_ID","SMART_MAIRA_ALLOWED_EMAILS","SMART_GEMINI_API_KEY"):
        monkeypatch.delenv(name,raising=False)
    assert import_status()["ready"] is False
    monkeypatch.setenv("SMART_GEMINI_API_KEY","test-key")
    assert import_status()["ready"] is False
    monkeypatch.setenv("SMART_GOOGLE_CLIENT_ID","test-client")
    monkeypatch.setenv("SMART_MAIRA_ALLOWED_EMAILS","test@example.com")
    assert import_status()["ready"] is True


def test_detect_invalid_pdf():
    with pytest.raises(HTTPException) as e:
        _validate_file("process.pdf", b"fake PDF")
    assert e.value.status_code == 415


def test_refuse_oversized_document():
    with pytest.raises(HTTPException) as e:
        _validate_file("test.txt", b"a" * (6 * 1024 * 1024 + 1))
    assert e.value.status_code == 413


def test_accept_pdf_mime_signature():
    assert _validate_file("flow.pdf", b"%PDF-1.4\n...")[0] == ".pdf"


def test_parse_proposal_preserves_source_and_positions():
    p = _parse_proposal(valid_proposal())
    assert p.source_map[0].source_step == "2.1"
    assert p.workflow.nodes[1].config["position"]["y"] > 0


def test_refuse_invented_unmapped_node():
    raw = valid_proposal()
    raw["workflow"]["nodes"].insert(2,{"id":"ghost","kind":"FORM","label":"Invented"})
    raw["workflow"]["edges"]=[{"source":"i","target":"uno"},{"source":"uno","target":"ghost"},{"source":"ghost","target":"f"}]
    with pytest.raises(ValueError,match="unmapped"):
        _parse_proposal(raw)


def test_refuse_circular_dependency():
    raw = valid_proposal()
    raw["workflow"]["edges"].append({"source":"uno","target":"uno"})
    with pytest.raises(ValueError,match="invalid dependencies"):
        _parse_proposal(raw)


def test_import_route_not_public_when_google_not_configured(testing, monkeypatch):
    client,_ = testing
    monkeypatch.delenv("SMART_GOOGLE_CLIENT_ID",raising=False)
    response=client.post('/api/v1/maira/workflow-import',files={'file':('flow.pdf',b'%PDF-1.4 fake','application/pdf')})
    assert response.status_code==503

def test_source_mapping_provenance_attached_to_workflow_nodes():
    proposal = _parse_proposal(valid_proposal())
    node = next(n for n in proposal.workflow.nodes if n.id == "uno")
    assert node.config["source_step"] == "2.1"
    assert node.config["source_excerpt"] == "CORREO CON DOCUMENTOS"
    assert node.config["source_page"] == 1
    assert node.config["source_confidence"] == "alta"


def test_conflicting_source_mapping_is_rejected():
    raw = valid_proposal()
    raw["workflow"]["nodes"][1]["config"] = {"source_step":"4.5"}
    with pytest.raises(ValueError,match="evidence conflicts"):
        _parse_proposal(raw)


def test_duplicate_source_step_mapping_is_rejected():
    raw = valid_proposal()
    raw["workflow"]["nodes"].insert(2,{"id":"dos","kind":"NOTIFICATION","label":"Otro correo"})
    raw["workflow"]["edges"]=[{"source":"i","target":"uno"},{"source":"uno","target":"dos"},{"source":"dos","target":"f"}]
    raw["source_map"].append({"source_step":"2.1","node_id":"dos","source_excerpt":"OTRO CORREO"})
    with pytest.raises(ValueError,match="repeated a source step"):
        _parse_proposal(raw)


def test_node_cannot_map_to_two_different_steps():
    raw = valid_proposal()
    raw["source_map"].append({"source_step":"2.2","node_id":"uno","source_excerpt":"AVISO AUTOMATICO"})
    with pytest.raises(ValueError,match="one node to multiple"):
        _parse_proposal(raw)

def test_session_denies_requests_without_google_id_token(testing):
    client,_=testing
    response=client.get("/api/v1/maira/session")
    assert response.status_code in (401,503)


def test_session_requires_email_allowlist(testing, monkeypatch):
    client,_=testing
    monkeypatch.setenv("SMART_GOOGLE_CLIENT_ID","fake-web-client")
    monkeypatch.setenv("SMART_MAIRA_ALLOWED_EMAILS","pilot@example.com")
    response=client.get("/api/v1/maira/session",headers={"Authorization":"Bearer fake-token"})
    assert response.status_code == 401


def test_persona_juridica_aspirante_mismatch_is_flagged(testing, monkeypatch):
    from app.main import app
    from app.routers import maira
    client,_ = testing
    monkeypatch.setenv("SMART_GEMINI_API_KEY","fake-test-key")
    app.dependency_overrides[maira._verify_identity] = lambda: "admin@example.com"
    captured={}
    async def fake_gemini(data,suffix,filename,api_key,party_kind=None):
        captured["kind"]=party_kind
        payload=valid_proposal()
        payload["workflow"]["nodes"][1]["label"]="Registro de personal aspirante"
        payload["workflow"]["nodes"][1]["role"]="ASPIRANTE"
        return maira._parse_proposal(payload)
    monkeypatch.setattr(maira,"_call_gemini",fake_gemini)
    try:
        resp=client.post("/api/v1/maira/workflow-import",
          files={"file":("flujo.pdf",b"%PDF-1.4 simulated","application/pdf")},
          data={"party_kind":"JURIDICA"})
        assert resp.status_code==200,resp.text
        assert captured["kind"]=="JURIDICA"
        assert any("persona jurídica" in x for x in resp.json()["observations"])
        assert resp.json()["mapped_steps"]==1
    finally:
        app.dependency_overrides.pop(maira._verify_identity,None)


@pytest.mark.parametrize("status,payload,expected", [
    (400, {"error":{"status":"INVALID_ARGUMENT","message":"invalid parameter"}},"parámetros"),
    (400, {"error":{"status":"INVALID_ARGUMENT","message":"API key not valid: SECRET_NOT_FOR_USERS"}},"clave API"),
    (403, {"error":{"status":"PERMISSION_DENIED","message":"private details"}},"negó acceso"),
    (404, {"error":{"status":"NOT_FOUND","message":"private details"}},"modelo"),
    (429, {"error":{"status":"RESOURCE_EXHAUSTED","message":"billing details"}},"cuota"),
    (503, {"error":{"status":"UNAVAILABLE","message":"private details"}},"indisponible")
])
def test_provider_error_classifies_without_exposing_upstream(status,payload,expected):
    from app.routers.maira import _provider_failure
    exception=_provider_failure(status,payload)
    assert exception.status_code==502
    assert expected in exception.detail
    assert "SECRET_NOT_FOR_USERS" not in exception.detail
    assert "private details" not in exception.detail

def test_gemini_connection_check_is_authenticated(testing,monkeypatch):
    from app.main import app
    from app.routers import maira
    client,_=testing
    monkeypatch.setenv("SMART_GEMINI_API_KEY","dummy")
    monkeypatch.setenv("SMART_GOOGLE_CLIENT_ID","mock-client")
    monkeypatch.setenv("SMART_MAIRA_ALLOWED_EMAILS","allowed@example.com")
    no_token=client.post("/api/v1/maira/workflow-import/check-connection")
    assert no_token.status_code==401
    app.dependency_overrides[maira._verify_identity]=lambda:"allowed@example.com"
    captured={}
    async def fake_request(payload,api_key,model,timeout):
        captured["api_key"]=api_key
        captured["model"]=model
        captured["timeout"]=timeout
        captured["payload"]=payload
        return {"candidates":[{"content":{"parts":[{"text":"OK"}]}}]}
    monkeypatch.setattr(maira,"_post_gemini",fake_request)
    try:
        response=client.post("/api/v1/maira/workflow-import/check-connection")
        assert response.status_code==200,response.text
        assert response.json()["connected"] is True
        assert response.json()["model"]=="gemini-3.6-flash"
        assert captured["api_key"]=="dummy"
        assert captured["timeout"]<=20
        assert "PDF" not in str(captured["payload"])
        assert "dummy" not in response.text
    finally:
        app.dependency_overrides.pop(maira._verify_identity,None)

def test_connection_check_reports_provider_failure_without_secret(testing,monkeypatch):
    from app.main import app
    from app.routers import maira
    client,_=testing
    monkeypatch.setenv("SMART_GEMINI_API_KEY","hidden")
    app.dependency_overrides[maira._verify_identity]=lambda:"allowed@example.com"
    async def fake_error(*args,**kwargs):
        raise maira._provider_failure(403,{"error":{"status":"PERMISSION_DENIED","message":"hidden key"}})
    monkeypatch.setattr(maira,"_post_gemini",fake_error)
    try:
        response=client.post("/api/v1/maira/workflow-import/check-connection")
        assert response.status_code==502
        assert "negó acceso" in response.json()["detail"]
        assert "hidden" not in response.text
    finally:
        app.dependency_overrides.pop(maira._verify_identity,None)


def test_model_env_override_is_honored_for_probe_and_document(monkeypatch):
    from app.routers import maira
    monkeypatch.setenv("SMART_GEMINI_MODEL","gemini-3.5-flash")
    assert maira._gemini_model()=="gemini-3.5-flash"
    monkeypatch.setenv("SMART_GEMINI_MODEL","gemini-3.6-flash/invalid")
    with pytest.raises(HTTPException) as err:
        maira._gemini_model()
    assert err.value.status_code==503

def test_current_model_is_not_retired_default(monkeypatch):
    from app.routers import maira
    monkeypatch.delenv("SMART_GEMINI_MODEL",raising=False)
    assert maira._gemini_model()=="gemini-3.6-flash"
