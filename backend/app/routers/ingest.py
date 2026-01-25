import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_async_session
from app.models.node import Node
from app.models.enums import EventType, NodeStatus
from app.schemas.node import IngestResponse, IngestTextRequest, NodeOut
from app.services.agent_structurer import run_structurer_mindmap
from app.services.events import get_or_create_event
from app.services.proposals import create_proposal

router = APIRouter(prefix="/ingest", tags=["ingest"], dependencies=[Depends(get_current_user)])


@router.post("/text", response_model=IngestResponse)
async def ingest_text(
    payload: IngestTextRequest, session: AsyncSession = Depends(get_async_session)
) -> IngestResponse:
    idempotency_key = payload.idempotency_key or f"text:{uuid.uuid4()}"
    event, created = await get_or_create_event(
        session,
        EventType.text_ingested,
        idempotency_key,
        {"source": payload.source.value},
    )
    if not created and event.payload.get("node_id"):
        node = await session.get(Node, event.payload["node_id"])
        return IngestResponse(
            node=NodeOut.model_validate(node),
            proposal_id=None,
            event_id=event.event_id,
            idempotent=True,
        )

    node = Node(
        raw_text=payload.text,
        status=NodeStatus.inbox,
        source=payload.source,
        tags=[],
        position={"x": 0, "y": 0},
    )
    session.add(node)
    await session.flush()

    event.payload["node_id"] = str(node.id)

    context_result = await session.execute(
        select(Node).order_by(Node.created_at.desc()).limit(30)
    )
    context_nodes = [
        {
            "id": str(n.id),
            "title": n.title,
            "tags": n.tags,
            "domain": n.domain,
        }
        for n in context_result.scalars().all()
    ]

    proposal_id = None
    try:
        proposal_json = run_structurer_mindmap(node.raw_text, context_nodes)
        proposal = await create_proposal(session, str(node.id), "StructurerMindmap", proposal_json)
        proposal_id = proposal.id
    except Exception:
        proposal_id = None

    await session.commit()

    return IngestResponse(
        node=NodeOut.model_validate(node),
        proposal_id=proposal_id,
        event_id=event.event_id,
        idempotent=False,
    )
