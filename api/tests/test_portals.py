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

def test_signature_and_integration_are_not_fake_completed(portal):
    create_pilot(portal)
    for kind in ["SIGNATURE", "INTEGRATION", "DOCUMENT_GENERATION"]:
        wf=sample_flow()
        wf["nodes"][2]["kind"]=kind
        wf["nodes"][2]["role"]="JURIDICO"
        r=portal.post("/api/v1/portal/workflows/publish",json={"workflow":wf})
        assert r.status_code==422 and "does not execute" in r.text

def test_cannot_assign_institutional_approval_to_contractor(portal):
    create_pilot(portal)
    wf=sample_flow()
    wf["nodes"][2]["config"]={"actor_side":"CONTRATISTA"}
    result=portal.post("/api/v1/portal/workflows/publish",json={"workflow":wf})
    assert result.status_code==422 and "Institutional approvals" in result.text

def create_party_record(client,name="Clínica Ficticia",email="clinica@example.com",kind="JURIDICA"):
    as_user("alice@example.com")
    result=client.post("/api/v1/portal/parties",json={"name":name,"email":email,"kind":kind})
    assert result.status_code==201,result.text
    return result.json()

def test_can_register_person_or_company_without_workflow(portal):
    create_pilot(portal)
    record=create_party_record(portal,email=None)
    assert record["case_count"]==0
    assert record["email"] is None
    assert portal.get("/api/v1/portal/workflows").json()==[]
    rows=portal.get("/api/v1/portal/parties").json()
    assert len(rows)==1 and rows[0]["name"]=="Clínica Ficticia"
    assert portal.get("/api/v1/portal/cases").json()==[]

def test_case_created_without_template_then_assigned_later(portal):
    create_pilot(portal)
    record=create_party_record(portal)
    response=portal.post("/api/v1/portal/cases",json={
        "title":"Borrador sin proceso","party_id":record["id"]
    })
    assert response.status_code==201,response.text
    item=response.json()
    assert item["state"]=="DRAFT"
    assert item["workflow_version_id"] is None
    assert item["party_id"]==record["id"]
    assert not item["invited"]
    detail=portal.get("/api/v1/portal/cases/"+item["id"])
    assert detail.status_code==200 and detail.json()["tasks"]==[]
    as_user("clinica@example.com")
    assert portal.get("/api/v1/portal/my-cases").json()==[]
    assert portal.get("/api/v1/portal/cases/"+item["id"]).status_code==404
    as_user("alice@example.com")
    template=portal.post("/api/v1/portal/workflows/publish",json={"workflow":sample_flow()})
    assert template.status_code==201
    bind=portal.post("/api/v1/portal/cases/"+item["id"]+"/workflow",
                     json={"workflow_id":template.json()["id"]})
    assert bind.status_code==200,bind.text
    assert bind.json()["state"]=="IN_PROGRESS"
    assert bind.json()["invited"]
    assert bind.json()["workflow_version_id"]==template.json()["id"]
    assert portal.post("/api/v1/portal/cases/"+item["id"]+"/workflow",
                     json={"workflow_id":template.json()["id"]}).status_code==409
    as_user("clinica@example.com")
    assert len(portal.get("/api/v1/portal/my-cases").json())==1

def test_reuse_same_company_in_multiple_cases(portal):
    create_pilot(portal)
    record=create_party_record(portal)
    ids=[]
    for n in (1,2):
        r=portal.post("/api/v1/portal/cases",json={
             "title":f"Expediente independiente {n}","party_id":record["id"]})
        assert r.status_code==201
        ids.append(r.json()["id"])
    assert ids[0]!=ids[1]
    records=portal.get("/api/v1/portal/parties").json()
    assert len(records)==1 and records[0]["case_count"]==2

def test_draft_without_contact_requires_email_before_invitation(portal):
    create_pilot(portal)
    record=create_party_record(portal,email=None)
    case=portal.post("/api/v1/portal/cases",json={
         "party_id":record["id"],"title":"Draft no contact"}).json()
    template=portal.post("/api/v1/portal/workflows/publish",json={"workflow":sample_flow()}).json()
    path="/api/v1/portal/cases/"+case["id"]+"/workflow"
    fail=portal.post(path,json={"workflow_id":template["id"]})
    assert fail.status_code==422 and "email" in fail.text
    updated=portal.patch("/api/v1/portal/parties/"+record["id"],json={
        "email":"clinica@example.com"})
    assert updated.status_code==200
    done=portal.post(path,json={"workflow_id":template["id"]})
    assert done.status_code==200 and done.json()["invited"]

def test_reject_duplicate_party_and_cross_tenant_party_access(portal,testing):
    # The two-tenant testing fixture already has a member in tenant-b, but the
    # pilot membership must never be allowed to associate tenant-b records.
    create_pilot(portal)
    record=create_party_record(portal)
    duplicate=portal.post("/api/v1/portal/parties",json={
       "name":"clínica ficticia","email":"CLINICA@EXAMPLE.COM","kind":"JURIDICA"})
    assert duplicate.status_code==409
    as_user("charlie")
    assert portal.get("/api/v1/portal/parties").json()==[]
    assert portal.post("/api/v1/portal/cases",json={
      "title":"Attempt cross-tenant","party_id":record["id"]}).status_code==404
    assert portal.patch("/api/v1/portal/parties/"+record["id"],
      json={"email":"attacker@example.com"}).status_code==404

def test_reject_cross_tenant_workflow_assignment(portal):
    create_pilot(portal)
    record=create_party_record(portal)
    case=portal.post("/api/v1/portal/cases",json={
      "title":"Draft no template","party_id":record["id"]}).json()
    as_user("charlie")
    wf=portal.post("/api/v1/portal/workflows/publish",json={"workflow":sample_flow()})
    assert wf.status_code==201
    as_user("alice@example.com")
    bind=portal.post(f"/api/v1/portal/cases/{case['id']}/workflow",
      json={"workflow_id":wf.json()["id"]})
    assert bind.status_code==404
    detail=portal.get(f"/api/v1/portal/cases/{case['id']}").json()
    assert detail["case"]["state"]=="DRAFT"

def test_cannot_mix_inline_and_existing_party(portal):
    create_pilot(portal)
    record=create_party_record(portal)
    mixed=portal.post("/api/v1/portal/cases",json={
       "title":"No duplicated subject","party_id":record["id"],
       "party":{"name":"Other","kind":"NATURAL","email":"other@example.com"}})
    assert mixed.status_code==422

def test_registered_external_contact_can_login_before_workflow_but_sees_no_case(portal):
    create_pilot(portal)
    record=create_party_record(portal,name="Proveedor autónomo",email="usuario@example.com")
    as_user("usuario@example.com")
    session=portal.get("/api/v1/portal/session")
    assert session.status_code==200
    assert session.json()["registered_contact"] is True
    assert session.json()["institutions"]==[]
    assert portal.get("/api/v1/portal/my-cases").json()==[]
    assert portal.get("/api/v1/portal/parties").status_code==403
    assert portal.post("/api/v1/portal/cases",json={
       "title":"Unauthorized draft","party_id":record["id"]}).status_code==403


def proposal_for_previewer():
    return {"filename":"Ciclo de contratación v2.pdf",
        "workflow":{"key":"CICLO_V2_ORIGINAL","name":"Ciclo de contratación",
            "nodes":[
             {"id":"start","label":"Inicio","kind":"START","policy":"ORG_REQUIRED"},
             {"id":"step1","label":"Creación de usuarios y proyectos","kind":"VALIDATION",
               "role":"ADMINISTRADOR","config":{"actor_side":"CONTRATANTE","source_step":"1"}},
             {"id":"step2","label":"Registro de personal a contratar","kind":"FORM",
               "role":"ASPIRANTE","config":{"actor_side":"CONTRATISTA","source_step":"2"}},
             {"id":"end","label":"Fin","kind":"END","policy":"ORG_REQUIRED"}],
            "edges":[{"source":"start","target":"step1"},
                     {"source":"step1","target":"step2"},
                     {"source":"step2","target":"end"}],
            "metadata":{"source":"maira-document-import","draft":True}},
        "source_map":[{"source_step":"1","node_id":"step1",
            "source_excerpt":"CREACIÓN DE USUARIOS Y PROYECTOS","page":1,"confidence":"alta"},
             {"source_step":"2","node_id":"step2",
            "source_excerpt":"REGISTRO DE PERSONAL A CONTRATAR","page":1,"confidence":"alta"}],
        "questions":["Confirmar si ASPIRANTE aplica a persona jurídica"],
        "observations":["Documento de contratación de personal; adaptar antes de enviar al hospital"]}

def test_preview_saved_for_registered_hospital_without_activating_tasks(portal):
    create_pilot(portal)
    party=create_party_record(portal,name="Hospital Smart",kind="JURIDICA")
    base=f"/api/v1/portal/parties/{party['id']}/process-previews"
    save=portal.post(base,json=proposal_for_previewer())
    assert save.status_code==201,save.text
    result=save.json()
    assert result["status"]=="DRAFT_REVIEW"
    assert result["source_map"][1]["source_step"]=="2"
    assert result["workflow"]["nodes"][2]["config"]["source_step"]=="2"
    assert result["questions"]
    assert len(portal.get(base).json())==1
    detail=portal.get(base+"/"+result["id"])
    assert detail.status_code==200
    assert "REGISTRO DE PERSONAL" in detail.json()["source_map"][1]["source_excerpt"]
    assert portal.get("/api/v1/portal/cases").json()==[]
    assert portal.get("/api/v1/portal/workflows").json()==[]
    as_user("contacto@example.com")
    assert portal.get(base).status_code==403
    assert portal.get(base+"/"+result["id"]).status_code==403

def test_cannot_save_party_preview_from_other_tenant(portal):
    create_pilot(portal)
    party=create_party_record(portal,name="Hospital Smart",kind="JURIDICA")
    as_user("charlie")
    base=f"/api/v1/portal/parties/{party['id']}/process-previews"
    assert portal.get(base).status_code==404
    assert portal.post(base,json=proposal_for_previewer()).status_code in (403,404)

def test_reject_preview_with_invented_unmapped_node(portal):
    create_pilot(portal)
    party=create_party_record(portal)
    payload=proposal_for_previewer()
    payload["workflow"]["nodes"].insert(3,{"id":"invented","kind":"FORM","label":"Documento no mencionado"})
    payload["workflow"]["edges"]=[
        {"source":"start","target":"step1"},{"source":"step1","target":"step2"},
        {"source":"step2","target":"invented"},{"source":"invented","target":"end"}]
    r=portal.post(f"/api/v1/portal/parties/{party['id']}/process-previews",json=payload)
    assert r.status_code==422
    assert "unmapped" in r.text

def test_preview_does_not_give_external_case_access(portal):
    create_pilot(portal)
    party=create_party_record(portal,email="persona@example.com")
    as_user("alice@example.com")
    preview=portal.post(f"/api/v1/portal/parties/{party['id']}/process-previews",
                        json=proposal_for_previewer())
    assert preview.status_code==201
    as_user("persona@example.com")
    assert portal.get("/api/v1/portal/my-cases").json()==[]
    assert portal.get(f"/api/v1/portal/parties/{party['id']}/process-previews").status_code==403
