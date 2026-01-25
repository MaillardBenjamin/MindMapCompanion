import pytest

from app.models.enums import EventType
from app.services.events import get_or_create_event


@pytest.mark.asyncio
async def test_events_idempotence(db_session):
    event1, created1 = await get_or_create_event(
        db_session, EventType.text_ingested, "k1", {"foo": "bar"}
    )
    event2, created2 = await get_or_create_event(
        db_session, EventType.text_ingested, "k1", {"foo": "bar"}
    )
    assert created1 is True
    assert created2 is False
    assert event1.id == event2.id
