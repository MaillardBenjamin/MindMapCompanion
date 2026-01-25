import uuid

from pydantic import BaseModel, ConfigDict

from app.models.enums import ActionMode, ActionType


class ActionCreate(BaseModel):
    node_id: uuid.UUID
    action_type: ActionType
    mode: ActionMode = ActionMode.review
    config: dict = {}
    enabled: bool = True


class ActionUpdate(BaseModel):
    mode: ActionMode | None = None
    config: dict | None = None
    enabled: bool | None = None


class ActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    node_id: uuid.UUID
    action_type: ActionType
    mode: ActionMode
    config: dict
    enabled: bool


class ActionListOut(BaseModel):
    actions: list[ActionOut]
