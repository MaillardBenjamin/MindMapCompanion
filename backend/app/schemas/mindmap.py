from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List, Dict, Any


# Schemas pour Mindmap
class MindmapBase(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    name: str
    description: Optional[str] = None


class MindmapCreate(MindmapBase):
    pass


class MindmapUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class MindmapResponse(MindmapBase):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    
    id: int
    user_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# Schemas pour Node
class NodeBase(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
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
    model_config = ConfigDict(protected_namespaces=())
    
    label: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    parent_id: Optional[int] = None
    status: Optional[str] = None


class NodeResponse(NodeBase):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    
    id: int
    mindmap_id: int
    created_at: datetime
    updated_at: datetime


class NodeWithChildren(NodeResponse):
    model_config = ConfigDict(protected_namespaces=())
    
    children: List["NodeResponse"] = []
    triggers: List["TriggerResponse"] = []


# Schemas pour Trigger
class TriggerBase(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    trigger_type: str  # email_received, date_reached, cron, state_changed, manual
    enabled: Optional[bool] = True
    config: Optional[Dict[str, Any]] = None


class TriggerCreate(TriggerBase):
    node_id: int


class TriggerUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    trigger_type: Optional[str] = None
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class TriggerResponse(TriggerBase):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    
    id: int
    node_id: int
    last_fired_at: Optional[str] = None
    dedupe_key: Optional[str] = None


class TriggerWithActions(TriggerResponse):
    model_config = ConfigDict(protected_namespaces=())
    
    actions: List["ActionResponse"] = []


# Schemas pour Action
class ActionBase(BaseModel):
    model_config = ConfigDict(protected_namespaces=(), populate_by_name=True)
    
    name: str
    action_type: str = Field(alias="type")  # api_call, notification, task, script, email, etc.
    order: Optional[int] = 0
    enabled: Optional[bool] = True
    config: Optional[Dict[str, Any]] = None  # Pour email: {"to": "email@example.com", "subject": "...", "body": "..."}


class ActionCreate(ActionBase):
    trigger_id: int


class ActionUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=(), populate_by_name=True)
    
    name: Optional[str] = None
    action_type: Optional[str] = Field(default=None, alias="type")
    order: Optional[int] = None
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class ActionResponse(ActionBase):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    
    id: int
    trigger_id: int
    created_at: datetime
    updated_at: datetime


# Schema pour Mindmap complet avec nodes
class MindmapWithNodes(MindmapResponse):
    model_config = ConfigDict(protected_namespaces=())
    
    nodes: List[NodeWithChildren] = []


# Update forward references
NodeWithChildren.model_rebuild()
TriggerWithActions.model_rebuild()
