from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.edge import Edge
from app.models.enums import CreatedBy, ProposalStatus, NodeType
from app.models.node import Node
from app.models.proposal import Proposal


async def create_proposal(
    session: AsyncSession, node_id: str, agent_name: str, proposal_json: dict
) -> Proposal:
    proposal = Proposal(
        node_id=node_id, agent_name=agent_name, proposal_json=proposal_json
    )
    session.add(proposal)
    await session.flush()
    return proposal


async def apply_proposal(
    session: AsyncSession, proposal: Proposal, reviewed_by: str | None
) -> Proposal:
    proposal.status = ProposalStatus.approved
    proposal.reviewed_by = reviewed_by
    proposal.reviewed_at = datetime.now(tz=timezone.utc)

    result = await session.execute(select(Node).where(Node.id == proposal.node_id))
    node = result.scalar_one()
    payload = proposal.proposal_json

    node.title = payload.get("title") or node.title
    node_type = payload.get("type")
    if node_type:
        try:
            node.type = NodeType(node_type)
        except ValueError:
            node.type = node_type
    node.domain = payload.get("domain") or node.domain
    node.tags = payload.get("tags") or node.tags
    node.next_action = payload.get("nextAction") or node.next_action
    node.ai_meta = {
        "confidence": payload.get("confidence"),
        "rationale": payload.get("rationale"),
        "model": payload.get("model"),
    }

    links = payload.get("links") or []
    for link in links:
        if not link.get("toNodeId"):
            continue
        edge = Edge(
            from_node_id=node.id,
            to_node_id=link["toNodeId"],
            relation_type=link.get("relationType", "related"),
            confidence=link.get("confidence", 0.5),
            created_by=CreatedBy.ai,
        )
        session.add(edge)

    proposal.status = ProposalStatus.applied
    await session.flush()
    return proposal
