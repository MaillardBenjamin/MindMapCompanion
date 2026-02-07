import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import NodeSource, NodeStatus, NodeType


class IngestTextRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    text: str
    source: NodeSource = NodeSource.ui
    idempotency_key: str | None = None


class NodeUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    title: str | None = None
    type: NodeType | None = None
    status: NodeStatus | None = None
    domain: str | None = None
    tags: list[str] | None = None
    next_action: str | None = None
    position: dict | None = None
    due_date: datetime | None = None


class NodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    raw_text: str
    title: str | None
    type: NodeType | None
    status: NodeStatus
    domain: str | None
    tags: list[str]
    next_action: str | None
    source: NodeSource
    source_ref: dict
    position: dict
    ai_meta: dict
    due_date: datetime | None


class MindmapEdgeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    from_node_id: uuid.UUID
    to_node_id: uuid.UUID
    relation_type: str
    confidence: float
    created_by: str


class MindmapOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    nodes: list[NodeOut]
    edges: list[MindmapEdgeOut]


class IngestResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    node: NodeOut
    proposal_id: uuid.UUID | None = None
    event_id: uuid.UUID | None = None
    idempotent: bool = False
