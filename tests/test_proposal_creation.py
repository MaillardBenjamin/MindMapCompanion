import pytest

from app.models.enums import NodeSource, NodeStatus
from app.models.node import Node
from app.services.proposals import create_proposal


@pytest.mark.asyncio
async def test_proposal_creation(db_session):
    node = Node(
        raw_text="Test",
        status=NodeStatus.inbox,
        source=NodeSource.ui,
        tags=[],
        position={"x": 0, "y": 0},
    )
    db_session.add(node)
    await db_session.flush()

    proposal = await create_proposal(
        db_session, str(node.id), "StructurerMindmap", {"title": "T"}
    )
    assert proposal.node_id == node.id
