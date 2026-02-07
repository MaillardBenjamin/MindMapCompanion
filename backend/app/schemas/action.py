from pydantic import BaseModel, ConfigDict

from app.models.enums import ActionMode, ActionType


class ActionCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    node_id: int  # Integer pour compatibilité avec le système mindmap
    action_type: ActionType
    mode: ActionMode = ActionMode.review
    config: dict = {}
    enabled: bool = True
    name: str | None = None  # Optionnel, sera généré automatiquement si absent


class ActionUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    name: str | None = None
    mode: ActionMode | None = None
    config: dict | None = None
    enabled: bool | None = None


class ActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int  # Integer pour compatibilité avec le système mindmap
    node_id: int | None  # Nullable car peut ne pas être défini pour les anciennes actions
    name: str | None  # Nom de l'action
    action_type: ActionType | None  # Nullable car peut ne pas être défini pour les anciennes actions
    mode: ActionMode | None  # Nullable car peut ne pas être défini pour les anciennes actions
    config: dict | None
    enabled: bool


class ActionListOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    actions: list[ActionOut]
