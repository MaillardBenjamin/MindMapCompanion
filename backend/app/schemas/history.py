from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class HistoryItemOut(BaseModel):
    """Élément d'historique unifié"""
    id: str
    type: Literal[
        "agent_execution",
        "trigger_execution",
        "action_execution",
        "node_created",
        "node_updated",
        "trigger_created",
        "trigger_updated",
        "trigger_deleted",
        "action_created",
        "action_updated",
        "action_deleted",
        "event",
    ]
    created_at: datetime
    title: str
    description: str | None = None
    status: str | None = None  # success, failed, pending, etc.
    node_id: int | None = None  # Integer uniquement (compatible avec tables mindmap)
    node_label: str | None = None
    trigger_id: int | None = None  # Integer uniquement
    action_id: int | None = None  # Integer uniquement
    agent_id: int | None = None
    agent_name: str | None = None
    metadata: dict = {}


class HistoryListOut(BaseModel):
    """Liste d'historique"""
    items: list[HistoryItemOut]
    total: int
