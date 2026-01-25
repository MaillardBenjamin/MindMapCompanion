from pydantic import BaseModel

from app.models.enums import EventType


class EventSimulateRequest(BaseModel):
    event_type: EventType
    idempotency_key: str
    payload: dict = {}
