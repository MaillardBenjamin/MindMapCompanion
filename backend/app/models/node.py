import uuid
from datetime import datetime

from sqlalchemy import Enum, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import NodeSource, NodeStatus, NodeType


class Node(Base, TimestampMixin):
    __tablename__ = "nodes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    raw_text: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    type: Mapped[NodeType | None] = mapped_column(Enum(NodeType), nullable=True)
    status: Mapped[NodeStatus] = mapped_column(Enum(NodeStatus), default=NodeStatus.inbox)
    domain: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    next_action: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[NodeSource] = mapped_column(Enum(NodeSource), nullable=False)
    source_ref: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    position: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    ai_meta: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)