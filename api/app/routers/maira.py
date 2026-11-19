"""MAIRA's tool boundary stays disabled until Gemini and approvals are configured.
Never return fabricated proposals in production.
"""
from fastapi import APIRouter, Depends
from ..security import Actor, require_actor

router = APIRouter(prefix="/api/v1/maira", tags=["maira"])

@router.get("/capabilities")
def capabilities(actor: Actor = Depends(require_actor)):
    return {"agent": "MAIRA", "status": "NOT_CONFIGURED",
            "planned": ["document_analysis", "workflow_proposal", "contract_drafting", "case_guidance"],
            "executable_actions_enabled": False}
