"""Two-sided pilot contract flow: authorization, state, evidence and isolation."""
import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.routers.portals import verify_google_email
from app.models import Tenant, Membership

def sample_flow():
    return {"key":"RED_PILOTO","name":"Plantilla de prueba","modality_key":"custom",
       "nodes":[
        {"id":"start","label":"Inicio","kind":"START"},
        {"id":"docs","label":"Diligenciar información","kind":"FORM","role":"CONTRATISTA",
         "config":{"actor_side":"CONTRATISTA","fields":[{"key":"contacto","label":"Contacto","type":"text","required":True}]}},
        {"id":"review","label":"Validación institucional","kind":"APPROVAL","role":"JURIDICO",
         "config":{"actor_side":"CONTRATANTE"}},
        {"id":"end","label":"Fin","kind":"END"}],
       "edges":[{"source":"start","target":"docs"},{"source":"docs","target":"review"},{"source":"review","target":"end"}],
       "metadata":{}}

def as_user(email):
    app.dependency_overrides[verify_google_email]=lambda:email

@pytest.fixture()
def portal(testing,monkeypatch):
    client,token=testing
    monkeypatch.setenv("SMART_PORTAL_DEMO_ENABLED","true")
    monkeypatch.setenv("SMART_MAIRA_ALLOWED_EMAILS","alice@example.com")
    as_user("alice@example.com")
    try: yield client
    finally: app.dependency_overrides.pop(verify_google_email,None)

def create_pilot(client):
    as_user("alice@example.com")
    res=client.post("/api/v1/portal/demo/setup",json={"name":"Demo sin clientes"})
    assert res.status_code==201,res.text
    return res.json()["tenant_id"]

def create_case(client,contractor="persona@example.com"):
    as_user("alice@example.com")
    p=client.post("/api/v1/portal/workflows/publish",json={"workflow":sample_flow()})
    assert p.status_code==201,p.text
    c=client.post("/api/v1/portal/cases",json={"workflow_id":p.json()["id"],
        "title":"Contrato prueba","party":{"name":"Persona de prueba","kind":"NATURAL","email":contractor}})
    assert c.status_code==201,c.text
    return c.json()["id"]

def test_unauthenticated_google_access_is_denied(testing):
    client,_=testing
    result=client.get("/api/v1/portal/session")
    assert result.status_code in (401,503)

def test_only_allowlisted_account_can_bootstrap(portal):
    as_user("stranger@example.com")
    assert portal.post("/api/v1/portal/demo/setup",json={"name":"No autorizado"}).status_code==403
    as_user("alice@example.com")
    result=portal.post("/api/v1/portal/demo/setup",json={"name":"Empresa ficticia"})
    assert result.status_code==201
    assert result.json()["created"] is True
    again=portal.post("/api/v1/portal/demo/setup",json={"name":"Otra empresa"})
    assert again.status_code==201 and again.json()["created"] is False

def test_publish_create_case_partner_access_and_completion(portal):
    create_pilot(portal)
    case_id=create_case(portal)
    as_user("alice@example.com")
    internal=portal.get(f"/api/v1/portal/cases/{case_id}")
    assert internal.status_code==200
    tasks=internal.json()["tasks"]
    doc=next(t for t in tasks if t["node_id"]=="docs")
    review=next(t for t in tasks if t["node_id"]=="review")
    assert doc["state"]=="PENDING" and review["state"]=="WAITING"
    as_user("persona@example.com")
    listing=portal.get("/api/v1/portal/my-cases")
    assert listing.status_code==200 and len(listing.json())==1
    result=portal.get(f"/api/v1/portal/cases/{case_id}")
    assert result.status_code==200
    assert result.json()["side"]=="CONTRATISTA"
    assert [t["node_id"] for t in result.json()["tasks"]]==["docs"]
    assert "party_email" not in result.json()["case"]
    assert portal.post(f"/api/v1/portal/cases/{case_id}/tasks/{review['id']}/complete",json={}).status_code==403
    assert portal.post(f"/api/v1/portal/cases/{case_id}/tasks/{doc['id']}/complete",
                       json={"data":{},"note":"incompleto"}).status_code==422
    done=portal.post(f"/api/v1/portal/cases/{case_id}/tasks/{doc['id']}/complete",
                     json={"data":{"contacto":"Persona sintética"}})
    assert done.status_code==200,done.text
    as_user("alice@example.com")
    detail=portal.get(f"/api/v1/portal/cases/{case_id}").json()
    review=next(t for t in detail["tasks"] if t["node_id"]=="review")
    assert review["state"]=="PENDING"
    assert portal.post(f"/api/v1/portal/cases/{case_id}/tasks/{review['id']}/complete",
                       json={"data":{}}).json()["case_state"]=="COMPLETED"

def test_return_and_correct_contractors_task(portal):
    create_pilot(portal);case_id=create_case(portal)
    as_user("persona@example.com")
    doc=portal.get(f"/api/v1/portal/cases/{case_id}").json()["tasks"][0]
    assert portal.post(f"/api/v1/portal/cases/{case_id}/tasks/{doc['id']}/complete",
                       json={"data":{"contacto":"Primera versión"}}).status_code==200
    as_user("alice@example.com")
    ret=portal.post(f"/api/v1/portal/cases/{case_id}/tasks/{doc['id']}/return",
                    json={"reason":"Corrige la información antes de revisar."})
    assert ret.status_code==200,ret.text
    as_user("persona@example.com")
    again=portal.get(f"/api/v1/portal/cases/{case_id}").json()["tasks"][0]
    assert again["state"]=="RETURNED"
    assert again["note"]=="Corrige la información antes de revisar."
    assert portal.post(f"/api/v1/portal/cases/{case_id}/tasks/{doc['id']}/complete",
                       json={"data":{"contacto":"Corregido"}}).status_code==200

def test_invitations_isolated_by_email_and_tenant(portal):
    create_pilot(portal);case_id=create_case(portal)
    as_user("unknown@example.com")
    assert portal.get("/api/v1/portal/session").status_code==403
    assert portal.get("/api/v1/portal/my-cases").json()==[]
    assert portal.get(f"/api/v1/portal/cases/{case_id}").status_code==404
    as_user("bob")
    assert portal.get(f"/api/v1/portal/cases/{case_id}").status_code==404
    as_user("alice@example.com")
    assert portal.get(f"/api/v1/portal/cases/{case_id}").status_code==200

def test_conditional_flow_not_publishable(portal):
    create_pilot(portal)
    wf=sample_flow()
    wf["edges"][1]["when"]={"field":"unknown","op":"eq","value":True}
    p=portal.post("/api/v1/portal/workflows/publish",json={"workflow":wf})
    assert p.status_code==422 and "Conditional" in p.text

def test_pilot_feature_flag_required_for_setup(testing,monkeypatch):
    client,_=testing
    monkeypatch.setenv("SMART_MAIRA_ALLOWED_EMAILS","alice@example.com")
    monkeypatch.delenv("SMART_PORTAL_DEMO_ENABLED",raising=False)
    as_user("alice@example.com")
    try:
        assert client.post("/api/v1/portal/demo/setup",json={"name":"Pilot"}).status_code==403
    finally:
        app.dependency_overrides.pop(verify_google_email,None)
