from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..database import get_session
from ..models import WorkflowVersion, AuditEvent
from ..security import Actor, require_actor, require_role
from ..workflow.schema import WorkflowDefinition, WorkflowEvaluation
from ..workflow.validator import WorkflowInvalid, topological_order
from ..workflow.simulator import simulate

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])

class DraftRequest(BaseModel):
    workflow: WorkflowDefinition

@router.get("")
def list_workflows(actor: Actor = Depends(require_actor), db: Session = Depends(get_session)):
    records = db.scalars(select(WorkflowVersion).where(WorkflowVersion.tenant_id == actor.tenant_id).order_by(WorkflowVersion.created_at.desc())).all()
    return [{"id": x.id, "key": x.template_key, "version": x.version, "status": x.status,
             "name": x.definition.get("name")} for x in records]

@router.post("/validate")
def validate(payload: DraftRequest, actor: Actor = Depends(require_actor)):
    require_role(actor, "CONFIGURADOR", "ADMIN")
    try:
        ordered = topological_order(payload.workflow)
    except WorkflowInvalid as exc:
        raise HTTPException(422, {"problems": exc.problems})
    return {"valid": True, "node_count": len(ordered), "order": ordered}

@router.post("/simulate")
def preview(payload: WorkflowEvaluation, actor: Actor = Depends(require_actor)):
    require_role(actor, "CONFIGURADOR", "ADMIN")
    try:
        return {"statuses": simulate(payload.workflow, payload.facts, payload.completed_node_ids)}
    except WorkflowInvalid as exc:
        raise HTTPException(422, {"problems": exc.problems})

@router.post("", status_code=201)
def create_draft(payload: DraftRequest, actor: Actor = Depends(require_actor), db: Session = Depends(get_session)):
    require_role(actor, "CONFIGURADOR", "ADMIN")
    try:
        topological_order(payload.workflow)
    except WorkflowInvalid as exc:
        raise HTTPException(422, {"problems": exc.problems})
    number = db.scalar(select(func.max(WorkflowVersion.version)).where(
            WorkflowVersion.tenant_id == actor.tenant_id,
            WorkflowVersion.template_key == payload.workflow.key)) or 0
    workflow = WorkflowVersion(tenant_id=actor.tenant_id, template_key=payload.workflow.key,
       version=number + 1, definition=payload.workflow.model_dump(mode="json"), created_by=actor.user_id)
    db.add(workflow)
    db.flush()
    db.add(AuditEvent(tenant_id=actor.tenant_id, actor_id=actor.user_id,
        event_type="WORKFLOW_DRAFT_CREATED", object_id=workflow.id,
        payload={"key": workflow.template_key, "version": workflow.version}))
    db.commit()
    return {"id": workflow.id, "version": workflow.version, "status": workflow.status}

@router.get("/{workflow_id}")
def get_workflow(workflow_id: str, actor: Actor = Depends(require_actor), db: Session = Depends(get_session)):
    record = db.scalar(select(WorkflowVersion).where(
        WorkflowVersion.id == workflow_id, WorkflowVersion.tenant_id == actor.tenant_id))
    if not record: raise HTTPException(404, "Workflow not found")
    return {"id": record.id, "status": record.status, "version": record.version,
            "definition": record.definition}
