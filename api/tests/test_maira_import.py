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
