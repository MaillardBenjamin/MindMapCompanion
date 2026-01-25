import uuid

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import MailProvider


class MailCache(Base):
    __tablename__ = "mails_cache"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider: Mapped[MailProvider] = mapped_column(Enum(MailProvider), nullable=False)
    provider_message_id: Mapped[str] = mapped_column(String, nullable=False)
    from_addr: Mapped[str] = mapped_column(String, nullable=False)
    subject: Mapped[str] = mapped_column(String, nullable=True)
    snippet: Mapped[str] = mapped_column(String, nullable=True)
    received_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True))
    raw_payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    processed: Mapped[bool] = mapped_column(default=False)
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False)
