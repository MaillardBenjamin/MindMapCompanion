import uuid

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import CreatedBy, EdgeRelationType


class Edge(Base):
    __tablename__ = "edges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    from_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("nodes.id"), nullable=False
    )
    to_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("nodes.id"), nullable=False
    )
    relation_type: Mapped[EdgeRelationType] = mapped_column(
        Enum(EdgeRelationType), nullable=False
    )
    confidence: Mapped[float] = mapped_column(default=0.5)
    created_by: Mapped[CreatedBy] = mapped_column(Enum(CreatedBy), default=CreatedBy.ai)
