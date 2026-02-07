from sqlalchemy import Enum, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import ActionMode, ActionType


class Action(Base):
    """
    Modèle Action compatible avec le système mindmap (IDs Integer).
    
    Cette classe est utilisée par le router /actions pour créer des actions
    liées aux nœuds du système mindmap.
    
    Structure actuelle de la table:
    - id, trigger_id, name, order, enabled, config, created_at, updated_at, action_type, mode, node_id
    """
    __tablename__ = "actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    node_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Lié à nodes.id (Integer)
    trigger_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Lié à triggers.id (ancien système)
    
    # Champs communs
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    order: Mapped[int | None] = mapped_column(Integer, default=0, nullable=True)
    
    # Champs action
    action_type: Mapped[str | None] = mapped_column(Enum(ActionType), nullable=True)
    mode: Mapped[str | None] = mapped_column(Enum(ActionMode), default=ActionMode.review)
    config: Mapped[dict | None] = mapped_column(JSONB, default=dict, nullable=True)
    enabled: Mapped[bool | None] = mapped_column(default=True, nullable=True)
