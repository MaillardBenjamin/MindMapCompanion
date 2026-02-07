import uuid

from pydantic import BaseModel, ConfigDict

from app.models.enums import TriggerType


class TriggerCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    node_id: uuid.UUID
    trigger_type: TriggerType
    config: dict = {}
    enabled: bool = True
    dedupe_key: str | None = None


class TriggerUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    config: dict | None = None
    enabled: bool | None = None
    dedupe_key: str | None = None


class TriggerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    node_id: uuid.UUID
    trigger_type: TriggerType
    config: dict
    enabled: bool
    last_fired_at: str | None
    dedupe_key: str | None


class TriggerListOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    triggers: list[TriggerOut]
