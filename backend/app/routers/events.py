from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_async_session
from app.schemas.event import EventSimulateRequest
from app.services.events import get_or_create_event

router = APIRouter(prefix="/events", tags=["events"], dependencies=[Depends(get_current_user)])


@router.post("/simulate")
async def simulate_event(
    payload: EventSimulateRequest, session: AsyncSession = Depends(get_async_session)
) -> dict:
    event, created = await get_or_create_event(
        session, payload.event_type, payload.idempotency_key, payload.payload
    )
    await session.commit()
    return {"event_id": str(event.event_id), "created": created}
