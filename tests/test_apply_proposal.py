import pytest

from app.models.enums import NodeSource, NodeStatus
from app.models.node import Node
from app.services.proposals import apply_proposal, create_proposal


@pytest.mark.asyncio
async def test_apply_proposal_creates_edges(db_session):
    node_a = Node(
        raw_text="A",
        status=NodeStatus.inbox,
        source=NodeSource.ui,
        tags=[],
        position={"x": 0, "y": 0},
    )
    node_b = Node(
        raw_text="B",
        status=NodeStatus.inbox,
        source=NodeSource.ui,
        tags=[],
        position={"x": 0, "y": 0},
    )
    db_session.add_all([node_a, node_b])
    await db_session.flush()

    proposal = await create_proposal(
        db_session,
        str(node_a.id),
        "StructurerMindmap",
        {
            "title": "Title",
            "type": "idea",
            "domain": "projects",
            "tags": ["x"],
            "links": [
                {"toNodeId": str(node_b.id), "relationType": "related", "confidence": 0.8}
            ],
            "nextAction": "Do",
            "confidence": 0.8,
            "rationale": ["r"],
        },
    )
    await apply_proposal(db_session, proposal, reviewed_by="tester")

    assert node_a.title == "Title"
