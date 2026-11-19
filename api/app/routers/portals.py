"""Demo-only two-sided contracting: tenant-isolated templates, cases, invitations, tasks.
Google-verified emails authorize a limited pilot. Never use for legal signatures or client files.
"""
from __future__ import annotations
import os
import hashlib
from datetime import datetime, timezone
from typing import Any, Literal
import jwt
from fastapi import APIRouter, Depends, Header, HTTPException
from google.oauth2 import id_token
from google.auth.transport.requests import Request as GoogleRequest
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..database import get_session
from ..models import Tenant, Membership, WorkflowVersion, ContractCase, ContractParty, ContractCaseAccess, ContractTask, AuditEvent, now_utc
from ..workflow.schema import WorkflowDefinition
from ..workflow.validator import topological_order, WorkflowInvalid

router = APIRouter(prefix="/api/v1/portal", tags=["contracting-portals"])

def verify_google_email(authorization: str | None = Header(default=None)) -> str:
    client_id = os.getenv("SMART_GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        raise HTTPException(503, "Google sign-in not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Google sign-in required")
    token = authorization[7:].strip()
    if not token or len(token) > 8192:
        raise HTTPException(401, "Invalid Google credential")
    try:
        claims = id_token.verify_oauth2_token(token, GoogleRequest(), client_id)
    except Exception:
        raise HTTPException(401, "Google credential expired or invalid") from None
    email = str(claims.get("email") or "").strip().lower()
    if not email or str(claims.get("email_verified")).lower() != "true":
        raise HTTPException(401, "A verified Google email is required")
    return email

def _pilot_enabled() -> bool:
    return os.getenv("SMART_PORTAL_DEMO_ENABLED", "").lower() == "true"

def _allowed_bootstrap(email: str) -> bool:
    allowed = {e.strip().lower() for e in os.getenv("SMART_MAIRA_ALLOWED_EMAILS", "").split(",") if e.strip()}
    return _pilot_enabled() and email in allowed

def _memberships(db: Session, email: str):
    return db.scalars(select(Membership).join(Tenant, Tenant.id == Membership.tenant_id).where(
        Membership.user_id == email, Membership.active.is_(True), Tenant.active.is_(True)
    ).order_by(Membership.id)).all()

def _internal(db: Session, email: str) -> Membership:
    memberships = _memberships(db, email)
    good = [m for m in memberships if set(m.roles).intersection({"ADMIN","CONFIGURADOR","OPERADOR"})]
    if not good:
        raise HTTPException(403, "No contracting institution membership")
    return good[0]

def _operator(db: Session, email: str) -> Membership:
    m = _internal(db, email)
    if not set(m.roles).intersection({"ADMIN","CONFIGURADOR","OPERADOR"}):
        raise HTTPException(403, "Institutional permission required")
    return m

def _configurator(db: Session, email: str) -> Membership:
    m = _internal(db, email)
    if not set(m.roles).intersection({"ADMIN","CONFIGURADOR"}):
        raise HTTPException(403, "Configurator permission required")
    return m

def _event(db: Session, tenant: str, email: str, action: str, object_id: str, payload: dict):
    db.add(AuditEvent(tenant_id=tenant,actor_id=email,event_type=action,object_id=object_id,payload=payload))

def _case_for_internal(db: Session, id: str, m: Membership):
    c = db.scalar(select(ContractCase).where(ContractCase.id==id,ContractCase.tenant_id==m.tenant_id))
    if not c: raise HTTPException(404, "Case not found")
    return c

def _access(db: Session, id: str, email: str):
    return db.scalar(select(ContractCaseAccess).join(ContractCase,ContractCase.id==ContractCaseAccess.case_id)
      .where(ContractCaseAccess.case_id==id,ContractCaseAccess.email==email,
             ContractCaseAccess.active.is_(True),ContractCase.tenant_id==ContractCaseAccess.tenant_id))

def _case_for_external(db: Session, id: str, email: str):
    access = _access(db,id,email)
    if not access: raise HTTPException(404,"Case not found")
    c=db.get(ContractCase,id)
    if not c or c.tenant_id!=access.tenant_id: raise HTTPException(404,"Case not found")
    return c

def _internal_case(db: Session, c: ContractCase, email: str) -> bool:
    membership = db.scalar(select(Membership).where(
      Membership.tenant_id==c.tenant_id, Membership.user_id==email, Membership.active.is_(True)))
    return bool(membership and set(membership.roles).intersection({"ADMIN","CONFIGURADOR","OPERADOR"}))

def _task_payload(task: ContractTask, external: bool=False) -> dict[str,Any]:
    # Never expose one side's answers, confidential notes, or fields to the other.
    result={"id":task.id,"node_id":task.node_id,"label":task.label,"kind":task.kind,
            "side":task.side,"state":task.state,"fields":task.fields}
    if not external or task.side=="CONTRATISTA":
        result["answer"]=task.answer
        result["note"]=task.note
    return result

def _get_workflow(db: Session,c: ContractCase) -> WorkflowDefinition:
    w=db.scalar(select(WorkflowVersion).where(WorkflowVersion.id==c.workflow_version_id,
      WorkflowVersion.tenant_id==c.tenant_id))
    if not w: raise HTTPException(409,"Workflow unavailable")
    return WorkflowDefinition.model_validate(w.definition)

def _sync(db: Session,c: ContractCase):
    wf=_get_workflow(db,c)
    tasks=db.scalars(select(ContractTask).where(ContractTask.case_id==c.id,ContractTask.tenant_id==c.tenant_id)).all()
    by_id={t.node_id:t for t in tasks}
    # Only unconditional workflows are publishable in this pilot.
    for nid in topological_order(wf):
        t=by_id[nid]
        preds=[by_id[edge.source] for edge in wf.edges if edge.target==nid]
        ready=all(p.state=="COMPLETED" for p in preds)
        if t.kind=="START" or not next(n for n in wf.nodes if n.id==nid).enabled:
            t.state="COMPLETED"
        elif t.kind=="END" and ready: t.state="COMPLETED"
        elif t.state=="COMPLETED": pass
        elif not ready: t.state="WAITING"
        elif t.state=="RETURNED": pass
        else: t.state="PENDING"
    c.state = "COMPLETED" if all(t.state=="COMPLETED" for t in tasks) else "IN_PROGRESS"
    return tasks

class DemoSetup(BaseModel):
    name: str = Field(default="Institución piloto",min_length=2,max_length=150)

@router.get("/session")
def session(email: str=Depends(verify_google_email),db:Session=Depends(get_session)):
    memberships=_memberships(db,email)
    assignments=db.scalars(select(ContractCaseAccess).where(
      ContractCaseAccess.email==email, ContractCaseAccess.active.is_(True))).all()
    registered=db.scalar(select(ContractParty.id).join(Tenant,Tenant.id==ContractParty.tenant_id).where(
        ContractParty.contact_email==email,Tenant.active.is_(True)))
    if not memberships and not assignments and not registered and not _allowed_bootstrap(email):
        raise HTTPException(403,"No institution, registration or invitation for this account")
    return {"email":email,"institutions":[{"id":m.tenant_id,"roles":m.roles} for m in memberships],
            "invited_cases":len(assignments),"registered_contact":bool(registered),
            "can_setup":_allowed_bootstrap(email) and not memberships,"pilot":True}

@router.post("/demo/setup",status_code=201)
def setup(payload:DemoSetup,email:str=Depends(verify_google_email),db:Session=Depends(get_session)):
    if not _allowed_bootstrap(email): raise HTTPException(403,"Pilot setup is disabled")
    existing=_memberships(db,email)
    if existing: return {"tenant_id":existing[0].tenant_id,"created":False}
    slug="pilot-"+hashlib.sha256(email.encode()).hexdigest()[:12]
    tenant=db.scalar(select(Tenant).where(Tenant.slug==slug))
    if not tenant:
        tenant=Tenant(slug=slug,name=payload.name)
        db.add(tenant);db.flush()
    db.add(Membership(tenant_id=tenant.id,user_id=email,roles=["ADMIN","CONFIGURADOR","OPERADOR"]))
    _event(db,tenant.id,email,"PILOT_TENANT_CREATED",tenant.id,{"name":payload.name})
    db.commit()
    return {"tenant_id":tenant.id,"created":True}

class PublishInput(BaseModel):
    workflow: WorkflowDefinition

@router.get("/workflows")
def workflows(email:str=Depends(verify_google_email),db:Session=Depends(get_session)):
    m=_operator(db,email)
    rows=db.scalars(select(WorkflowVersion).where(WorkflowVersion.tenant_id==m.tenant_id,
        WorkflowVersion.status=="PUBLISHED").order_by(WorkflowVersion.created_at.desc())).all()
    return [{"id":w.id,"name":w.definition.get("name"),"key":w.template_key,"version":w.version} for w in rows]

@router.post("/workflows/publish",status_code=201)
def publish(input:PublishInput,email:str=Depends(verify_google_email),db:Session=Depends(get_session)):
    m=_configurator(db,email);wf=input.workflow
    try: topological_order(wf)
    except WorkflowInvalid as exc: raise HTTPException(422,{"problems":exc.problems})
    # Do not silently execute conditional branches, external APIs, or signatures as valid legal acts.
    if any(n.when is not None or n.policy=="CONDITIONAL" for n in wf.nodes) or any(e.when is not None for e in wf.edges):
        raise HTTPException(422,"Conditional routing is not executable in this pilot")
    if len(wf.nodes)>160: raise HTTPException(422,"Pilot limited to 160 nodes")
    unsupported = sorted({n.kind for n in wf.nodes if n.enabled and n.kind not in
       {"START","END","FORM","DOCUMENT_REQUEST","DOCUMENT_REVIEW","VALIDATION","APPROVAL","HUMAN_DECISION"}})
    if unsupported:
        raise HTTPException(422, "Pilot does not execute: " + ", ".join(unsupported))
    if any(not n.enabled for n in wf.nodes):
        raise HTTPException(422,"Disabled workflow nodes are not executable in this pilot")
    if any(n.kind=="APPROVAL" and n.config.get("actor_side")=="CONTRATISTA" for n in wf.nodes):
        raise HTTPException(422,"Institutional approvals cannot be assigned to contractors in this pilot")
    if any(n.kind in ("FORM","DOCUMENT_REQUEST") and n.config.get("execution_mode") in ("AI_ASSISTED","API","RPA") for n in wf.nodes):
        raise HTTPException(422,"Automated execution not enabled in this pilot")
    number=db.scalar(select(func.max(WorkflowVersion.version)).where(
        WorkflowVersion.tenant_id==m.tenant_id, WorkflowVersion.template_key==wf.key)) or 0
    w=WorkflowVersion(tenant_id=m.tenant_id,template_key=wf.key,version=number+1,
       status="PUBLISHED",definition=wf.model_dump(mode="json"),created_by=email,published_by=email)
    db.add(w);db.flush()
    _event(db,m.tenant_id,email,"PILOT_WORKFLOW_PUBLISHED",w.id,{"key":wf.key,"version":w.version})
    db.commit()
    return {"id":w.id,"version":w.version,"status":w.status,"pilot":True}

class PartyInput(BaseModel):
    name: str = Field(min_length=2,max_length=250)
    email: EmailStr | None = None
    kind: Literal["NATURAL","JURIDICA"]

class PartyUpdate(BaseModel):
    name: str | None = Field(default=None,min_length=2,max_length=250)
    email: EmailStr | None = None

def _party_record(db: Session, tenant_id: str, party_id: str) -> ContractParty:
    party=db.scalar(select(ContractParty).where(
       ContractParty.id==party_id,ContractParty.tenant_id==tenant_id))
    if not party: raise HTTPException(404,"Person or company not found")
    return party

def _party_summary(db: Session, party: ContractParty) -> dict[str, Any]:
    total=db.scalar(select(func.count(ContractCase.id)).where(
       ContractCase.tenant_id==party.tenant_id,ContractCase.party_id==party.id)) or 0
    return {"id":party.id,"name":party.name,"kind":party.kind,
            "email":party.contact_email,"case_count":total}

@router.get("/parties")
def parties(email: str=Depends(verify_google_email),db: Session=Depends(get_session)):
    m=_operator(db,email)
    rows=db.scalars(select(ContractParty).where(ContractParty.tenant_id==m.tenant_id)
       .order_by(ContractParty.created_at.desc())).all()
    return [_party_summary(db,x) for x in rows]

@router.post("/parties",status_code=201)
def create_party(body: PartyInput,email: str=Depends(verify_google_email),db: Session=Depends(get_session)):
    m=_operator(db,email)
    name=body.name.strip()
    if len(name)<2:raise HTTPException(422,"Name is required")
    e=str(body.email).strip().lower() if body.email else None
    dup=db.scalar(select(ContractParty).where(ContractParty.tenant_id==m.tenant_id,
       func.lower(ContractParty.name)==name.lower(),ContractParty.kind==body.kind,
       ContractParty.contact_email==e))
    if dup:raise HTTPException(409,{"message":"This record already exists","id":dup.id})
    party=ContractParty(tenant_id=m.tenant_id,name=name,kind=body.kind,contact_email=e)
    db.add(party);db.flush()
    _event(db,m.tenant_id,email,"PARTY_CREATED",party.id,{"kind":party.kind})
    db.commit()
    return _party_summary(db,party)

@router.patch("/parties/{party_id}")
def update_party(party_id: str,body: PartyUpdate,email: str=Depends(verify_google_email),
                 db: Session=Depends(get_session)):
    m=_operator(db,email)
    party=_party_record(db,m.tenant_id,party_id)
    fields=body.model_fields_set
    if "name" in fields:
        if not body.name or len(body.name.strip())<2:raise HTTPException(422,"Invalid name")
        party.name=body.name.strip()
    if "email" in fields:
        party.contact_email=str(body.email).strip().lower() if body.email else None
    _event(db,m.tenant_id,email,"PARTY_UPDATED",party.id,{"changed":sorted(fields)})
    db.commit()
    return _party_summary(db,party)

class CaseInput(BaseModel):
    workflow_id: str | None = None
    party_id: str | None = None
    title: str = Field(min_length=3,max_length=250)
    party: PartyInput | None = None  # Supports legacy V6.3 request shape.

class AttachWorkflowInput(BaseModel):
    workflow_id: str = Field(min_length=1)

def _published_workflow(db: Session, tenant_id: str, workflow_id: str) -> WorkflowVersion:
    w=db.scalar(select(WorkflowVersion).where(WorkflowVersion.id==workflow_id,
          WorkflowVersion.tenant_id==tenant_id,WorkflowVersion.status=="PUBLISHED"))
    if not w: raise HTTPException(404,"Published template not found")
    return w

def _bind_workflow(db: Session, c: ContractCase, w: WorkflowVersion, party: ContractParty, actor: str):
    if c.workflow_version_id or db.scalar(select(ContractTask.id).where(
        ContractTask.case_id==c.id,ContractTask.tenant_id==c.tenant_id)):
        raise HTTPException(409,"This case already has a workflow")
    if not party.contact_email:
        raise HTTPException(422,"Add an authorized contact email to the person or company before activating a workflow")
    wf=WorkflowDefinition.model_validate(w.definition)
    c.workflow_version_id=w.id
    db.add(ContractCaseAccess(tenant_id=c.tenant_id,case_id=c.id,party_id=party.id,
              email=party.contact_email))
    for n in wf.nodes:
        side=n.config.get("actor_side")
        if side not in ("CONTRATANTE","CONTRATISTA"):
            side="CONTRATISTA" if (n.role or "").upper() in (
               "CONTRATISTA","PRESTADOR","PROVEEDOR","ASPIRANTE") else "CONTRATANTE"
        db.add(ContractTask(tenant_id=c.tenant_id,case_id=c.id,node_id=n.id,
             label=n.label[:250],kind=n.kind,side=side,fields=n.config.get("fields",[])))
    db.flush();_sync(db,c)
    _event(db,c.tenant_id,actor,"WORKFLOW_ASSIGNED",c.id,
       {"workflow_id":w.id,"party_id":party.id,"invited":True})

def _case_summary(db:Session,c:ContractCase,include_email:bool=True):
    a=db.scalar(select(ContractCaseAccess).where(
       ContractCaseAccess.case_id==c.id,ContractCaseAccess.tenant_id==c.tenant_id))
    party=db.get(ContractParty,c.party_id or (a.party_id if a else None)) if (c.party_id or a) else None
    tasks=db.scalars(select(ContractTask).where(ContractTask.case_id==c.id,
       ContractTask.tenant_id==c.tenant_id)).all()
    result={"id":c.id,"title":c.title,"state":c.state,
            "workflow_version_id":c.workflow_version_id,"party_id":party.id if party else None,
            "party_name":party.name if party else None,
            "invited":bool(a and a.active),
            "total":len([t for t in tasks if t.kind not in ("START","END")]),
            "completed":len([t for t in tasks if t.kind not in ("START","END") and t.state=="COMPLETED"])}
    if include_email:result["party_email"]=a.email if a else (party.contact_email if party else None)
    return result

@router.post("/cases",status_code=201)
def create_case(body:CaseInput,email:str=Depends(verify_google_email),db:Session=Depends(get_session)):
    m=_operator(db,email)
    if bool(body.party_id)==bool(body.party):
        raise HTTPException(422,"Choose exactly one existing person/company or provide a new record")
    if body.party_id:
        party=_party_record(db,m.tenant_id,body.party_id)
    else:
        assert body.party is not None
        party=ContractParty(tenant_id=m.tenant_id,name=body.party.name.strip(),
             kind=body.party.kind,contact_email=str(body.party.email).lower() if body.party.email else None)
        db.add(party);db.flush()
    w=_published_workflow(db,m.tenant_id,body.workflow_id) if body.workflow_id else None
    if w and not party.contact_email:
        raise HTTPException(422,"Add the contact email before activating the workflow")
    c=ContractCase(tenant_id=m.tenant_id,party_id=party.id,
       workflow_version_id=None,title=body.title.strip(),state="DRAFT",case_data={"pilot":True})
    db.add(c);db.flush()
    if w:_bind_workflow(db,c,w,party,email)
    _event(db,m.tenant_id,email,"PILOT_CASE_CREATED",c.id,
       {"party_id":party.id,"workflow_id":w.id if w else None,"draft":w is None})
    db.commit()
    return _case_summary(db,c)

@router.post("/cases/{case_id}/workflow")
def assign_case_workflow(case_id:str,body:AttachWorkflowInput,
              email:str=Depends(verify_google_email),db:Session=Depends(get_session)):
    m=_operator(db,email)
    c=_case_for_internal(db,case_id,m)
    if c.workflow_version_id or c.state!="DRAFT":
        raise HTTPException(409,"Only draft cases without a template can be assigned")
    if not c.party_id:raise HTTPException(409,"Case has no registered person/company")
    party=_party_record(db,m.tenant_id,c.party_id)
    w=_published_workflow(db,m.tenant_id,body.workflow_id)
    _bind_workflow(db,c,w,party,email)
    db.commit()
    return _case_summary(db,c)

@router.get("/cases")
def institution_cases(email:str=Depends(verify_google_email),db:Session=Depends(get_session)):
    m=_operator(db,email)
    rows=db.scalars(select(ContractCase).where(ContractCase.tenant_id==m.tenant_id)
      .order_by(ContractCase.created_at.desc())).all()
    return [_case_summary(db,c) for c in rows]

@router.get("/my-cases")
def my_cases(email:str=Depends(verify_google_email),db:Session=Depends(get_session)):
    rows=db.scalars(select(ContractCase).join(ContractCaseAccess,ContractCase.id==ContractCaseAccess.case_id)
       .where(ContractCaseAccess.email==email,ContractCaseAccess.active.is_(True),
              ContractCase.tenant_id==ContractCaseAccess.tenant_id)
       .order_by(ContractCase.created_at.desc())).all()
    return [_case_summary(db,c,include_email=False) for c in rows]

@router.get("/cases/{case_id}")
def detail(case_id:str,email:str=Depends(verify_google_email),db:Session=Depends(get_session)):
    c=db.get(ContractCase,case_id)
    if not c:raise HTTPException(404,"Case not found")
    internal=_internal_case(db,c,email)
    if not internal:_case_for_external(db,case_id,email)
    tasks=db.scalars(select(ContractTask).where(ContractTask.case_id==c.id,
           ContractTask.tenant_id==c.tenant_id)).all()
    if c.workflow_version_id:
        wf=_get_workflow(db,c)
        order=topological_order(wf)
    else:
        order=[]
    lookup={t.node_id:t for t in tasks}
    return {"case":_case_summary(db,c,include_email=internal),
       "side":"CONTRATANTE" if internal else "CONTRATISTA",
       "tasks":[_task_payload(lookup[n],external=not internal) for n in order
                if n in lookup and (internal or lookup[n].side=="CONTRATISTA")]}

class TaskAnswer(BaseModel):
    data:dict[str,Any]=Field(default_factory=dict)
    note:str=Field(default="",max_length=2000)

@router.post("/cases/{case_id}/tasks/{task_id}/complete")
def complete_task(case_id:str,task_id:str,body:TaskAnswer,email:str=Depends(verify_google_email),
                  db:Session=Depends(get_session)):
    c=db.get(ContractCase,case_id)
    if not c:raise HTTPException(404,"Case not found")
    internal=_internal_case(db,c,email)
    if not internal:_case_for_external(db,case_id,email)
    task=db.scalar(select(ContractTask).where(ContractTask.id==task_id,ContractTask.case_id==case_id,
                                        ContractTask.tenant_id==c.tenant_id))
    if not task:raise HTTPException(404,"Task not found")
    if (internal and task.side!="CONTRATANTE") or (not internal and task.side!="CONTRATISTA"):
        raise HTTPException(403,"Task belongs to the other portal")
    if task.state not in ("PENDING","RETURNED"):raise HTTPException(409,"Task is not available")
    if task.kind in ("START","END"):raise HTTPException(409,"Automatic workflow node")
    if len(body.data)>50 or len(str(body.data))>15000:raise HTTPException(422,"Too much answer data")
    allowed={field.get("key"):field for field in task.fields if isinstance(field,dict)}
    if set(body.data)-set(allowed):raise HTTPException(422,"Unexpected form field")
    for key,field in allowed.items():
        if field.get("required") and body.data.get(key) in (None,"",[]):
            raise HTTPException(422,f"Required field: {key}")
    task.answer=body.data;task.note=body.note;task.state="COMPLETED";task.updated_at=now_utc()
    _event(db,c.tenant_id,email,"PILOT_TASK_COMPLETED",c.id,{"node_id":task.node_id,"side":task.side})
    _sync(db,c);db.commit()
    return {"case_state":c.state,"task_state":task.state}

class ReturnInput(BaseModel):
    reason:str=Field(min_length=5,max_length=2000)

@router.post("/cases/{case_id}/tasks/{task_id}/return")
def return_task(case_id:str,task_id:str,body:ReturnInput,
                email:str=Depends(verify_google_email),db:Session=Depends(get_session)):
    m=_operator(db,email)
    c=_case_for_internal(db,case_id,m)
    task=db.scalar(select(ContractTask).where(ContractTask.id==task_id,ContractTask.case_id==case_id,
                                               ContractTask.tenant_id==m.tenant_id))
    if not task:raise HTTPException(404,"Task not found")
    if task.side!="CONTRATISTA" or task.state!="COMPLETED":
        raise HTTPException(409,"Only completed contractor tasks can be returned")
    wf=_get_workflow(db,c)
    downstream=set();pending={task.node_id}
    while pending:
        n=pending.pop()
        for edge in wf.edges:
            if edge.source==n and edge.target not in downstream:
                downstream.add(edge.target);pending.add(edge.target)
    progressed=db.scalars(select(ContractTask).where(ContractTask.case_id==c.id,
                               ContractTask.node_id.in_(downstream))).all()
    if any(t.state=="COMPLETED" and t.kind not in ("END",) for t in progressed):
        raise HTTPException(409,"Downstream work has already been completed")
    task.state="RETURNED";task.note=body.reason;task.updated_at=now_utc()
    _event(db,m.tenant_id,email,"PILOT_TASK_RETURNED",c.id,{"node_id":task.node_id,"reason":body.reason})
    _sync(db,c);db.commit()
    return {"case_state":c.state,"task_state":task.state}
