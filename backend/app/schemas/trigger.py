import uuid

from pydantic import BaseModel, ConfigDict

from app.models.enums import TriggerType


class TriggerCreate(BaseModel):
    node_id: uuid.UUID
    trigger_type: TriggerType
    config: dict = {}
    enabled: bool = True
    dedupe_key: str | None = None


class TriggerUpdate(BaseModel):
    config: dict | None = None
    enabled: bool | None = None
    dedupe_key: str | None = None


class TriggerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    node_id: uuid.UUID
    trigger_type: TriggerType
    config: dict
    enabled: bool
    last_fired_at: str | None
    dedupe_key: str | None


class TriggerListOut(BaseModel):
    triggers: list[TriggerOut]
