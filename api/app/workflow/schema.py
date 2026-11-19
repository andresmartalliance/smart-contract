from typing import Literal, Any
from pydantic import BaseModel, Field, model_validator

NodeType = Literal["START","FORM","DOCUMENT_REQUEST","DOCUMENT_REVIEW","VALIDATION",
  "APPROVAL","NEGOTIATION","CALCULATION","DOCUMENT_GENERATION","SIGNATURE",
  "NOTIFICATION","INTEGRATION","TIMER","JOIN","HUMAN_DECISION","END"]
PolicyType = Literal["LEGAL_LOCKED", "ORG_REQUIRED", "CONDITIONAL", "OPTIONAL"]

class Condition(BaseModel):
    field: str = Field(min_length=1)
    op: Literal["eq", "neq", "in", "gt", "gte", "lt", "lte", "exists"]
    value: Any = None

class Node(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1)
    kind: NodeType
    enabled: bool = True
    policy: PolicyType = "OPTIONAL"
    role: str | None = None
    when: Condition | None = None
    config: dict[str, Any] = Field(default_factory=dict)

class Edge(BaseModel):
    source: str
    target: str
    when: Condition | None = None

class WorkflowDefinition(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1)
    modality_key: str | None = None  # Freely configurable, NOT a fixed enum.
    nodes: list[Node] = Field(min_length=2)
    edges: list[Edge]
    metadata: dict[str, Any] = Field(default_factory=dict)

class WorkflowEvaluation(BaseModel):
    workflow: WorkflowDefinition
    facts: dict[str, Any] = Field(default_factory=dict)
    completed_node_ids: set[str] = Field(default_factory=set)
