import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.enums import EventType


async def get_or_create_event(
    session: AsyncSession,
    event_type: EventType,
    idempotency_key: str,
    payload: dict,
) -> tuple[Event, bool]:
    result = await session.execute(
        select(Event).where(
            Event.idempotency_key == idempotency_key, Event.event_type == event_type
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing, False
    event = Event(
        event_id=uuid.uuid4(),
        event_type=event_type,
        idempotency_key=idempotency_key,
        payload=payload,
    )
    session.add(event)
    await session.flush()
    return event, True
