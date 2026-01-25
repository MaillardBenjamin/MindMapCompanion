import os
from datetime import datetime, timedelta, timezone

import pytest

os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/personal_assistant_test",
)

from app.models.action import Action
from app.models.enums import ActionMode, ActionType, NodeSource, NodeStatus, TriggerType
from app.models.node import Node
from app.models.trigger import Trigger
from app.services.scheduler import run_due_triggers
from sqlalchemy import text


@pytest.mark.asyncio
async def test_scheduler_triggers_reminder(db_session):
    node = Node(
        raw_text="Reminder",
        status=NodeStatus.ready,
        source=NodeSource.ui,
        tags=[],
        position={"x": 0, "y": 0},
    )
    db_session.add(node)
    await db_session.flush()

    trigger = Trigger(
        node_id=node.id,
        trigger_type=TriggerType.date_reached,
        config={"run_at": (datetime.now(tz=timezone.utc) - timedelta(minutes=1)).isoformat()},
        enabled=True,
    )
    action = Action(
        node_id=node.id,
        action_type=ActionType.create_reminder,
        mode=ActionMode.review,
        config={"channel": "email"},
        enabled=True,
    )
    db_session.add_all([trigger, action])
    await db_session.commit()

    await run_due_triggers()

    logs = await db_session.execute(text("SELECT count(*) FROM execution_logs"))
    count = logs.scalar_one()
    assert count >= 1
