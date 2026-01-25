import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import ExecutionStatus


class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Utiliser Integer pour référencer les tables mindmap (nodes, triggers, actions)
    node_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("nodes.id"), nullable=True
    )
    trigger_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("triggers.id"), nullable=True
    )
    action_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("actions.id"), nullable=True
    )
    # Garder UUID pour proposal_id et event_id (ils utilisent UUID)
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("proposals.id"), nullable=True
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id"), nullable=True
    )
    idempotency_key: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[ExecutionStatus] = mapped_column(
        Enum(ExecutionStatus), default=ExecutionStatus.success
    )
    input_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    output_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
