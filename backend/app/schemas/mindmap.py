from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any


# Schemas pour Mindmap
class MindmapBase(BaseModel):
    name: str
    description: Optional[str] = None


class MindmapCreate(MindmapBase):
    pass


class MindmapUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class MindmapResponse(MindmapBase):
    id: int
    user_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Schemas pour Node
class NodeBase(BaseModel):
    label: str
    description: Optional[str] = None
    color: Optional[str] = "#00D9FF"
    position_x: int
    position_y: int
    parent_id: Optional[int] = None
    is_root: Optional[bool] = False
    status: Optional[str] = "idle"


class NodeCreate(NodeBase):
    mindmap_id: int


class NodeUpdate(BaseModel):
    label: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    parent_id: Optional[int] = None
    status: Optional[str] = None


class NodeResponse(NodeBase):
    id: int
    mindmap_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NodeWithChildren(NodeResponse):
    children: List["NodeResponse"] = []
    triggers: List["TriggerResponse"] = []


# Schemas pour Trigger
class TriggerBase(BaseModel):
    trigger_type: str  # email_received, date_reached, cron, state_changed, manual
    enabled: Optional[bool] = True
    config: Optional[Dict[str, Any]] = None


class TriggerCreate(TriggerBase):
    node_id: int


class TriggerUpdate(BaseModel):
    trigger_type: Optional[str] = None
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class TriggerResponse(TriggerBase):
    id: int
    node_id: int
    last_fired_at: Optional[str] = None
    dedupe_key: Optional[str] = None

    class Config:
        from_attributes = True


class TriggerWithActions(TriggerResponse):
    actions: List["ActionResponse"] = []


# Schemas pour Action
class ActionBase(BaseModel):
    name: str
    type: str  # api_call, notification, task, script, email, etc.
    order: Optional[int] = 0
    enabled: Optional[bool] = True
    config: Optional[Dict[str, Any]] = None  # Pour email: {"to": "email@example.com", "subject": "...", "body": "..."}


class ActionCreate(ActionBase):
    trigger_id: int


class ActionUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    order: Optional[int] = None
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class ActionResponse(ActionBase):
    id: int
    trigger_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Schema pour Mindmap complet avec nodes
class MindmapWithNodes(MindmapResponse):
    nodes: List[NodeWithChildren] = []


# Update forward references
NodeWithChildren.model_rebuild()
TriggerWithActions.model_rebuild()
