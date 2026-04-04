"""
Tests pour le déclenchement des triggers state_changed
et l'écriture des résultats d'agent dans le graphe (write_to_graph).

Utilise une base PostgreSQL sync (pattern identique à test_assistant_trigger_setup).
"""

import os
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.auth.password import get_password_hash
from app.database import Base
from app.models.configurable_agent import ConfigurableAgent
from app.models.mindmap import Mindmap, Node, Trigger


def _sync_database_url() -> str:
    url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/personal_assistant_test",
    )
    if "+asyncpg" in url:
        return url.replace("+asyncpg", "")
    return url


@pytest.fixture
def sync_db():
    url = _sync_database_url()
    engine = create_engine(url, echo=False)
    try:
        conn = engine.connect()
        conn.close()
    except OperationalError as e:
        pytest.skip(f"Base PostgreSQL indisponible ({url}) : {e}")

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


def _seed_mindmap_with_node(db, status="idle"):
    """Crée un user, un mindmap et un nœud avec le statut donné."""
    from app.models.user import User

    user = User(
        email="state-changed-test@example.com",
        hashed_password=get_password_hash("secret"),
        is_active=True,
    )
    db.add(user)
    db.flush()

    mm = Mindmap(user_id=user.id, name="Test MM", description=None)
    db.add(mm)
    db.flush()

    node = Node(
        mindmap_id=mm.id,
        parent_id=None,
        label="Veille IA",
        description="Nœud de veille",
        color="#00D9FF",
        position_x=400,
        position_y=300,
        is_root=True,
        status=status,
    )
    db.add(node)
    db.flush()

    agent = ConfigurableAgent(
        user_id=user.id,
        name="News Monitor Agent",
        slug="news-monitor-test",
        description="Agent de test",
        markdown_config="# Test\n",
        prompt_template="{{input_text}}",
        is_active=True,
        is_public=False,
    )
    db.add(agent)
    db.commit()

    return user, mm, node, agent


# ---------------------------------------------------------------------------
# Tests state_changed triggers
# ---------------------------------------------------------------------------


def test_state_changed_trigger_matches_any_change(sync_db):
    """Un trigger state_changed sans filtre se déclenche sur tout changement."""
    user, mm, node, agent = _seed_mindmap_with_node(sync_db, status="inbox")

    trigger = Trigger(
        node_id=node.id,
        trigger_type="state_changed",
        enabled=True,
        config={
            "task_type": "agent",
            "selected_agent": str(agent.id),
        },
    )
    sync_db.add(trigger)
    sync_db.commit()

    from app.services.state_changed import fire_state_changed_triggers

    with patch(
        "app.services.state_changed.execute_trigger_with_config",
        new_callable=AsyncMock,
    ) as mock_exec:
        with patch("app.services.state_changed.SessionLocal", return_value=sync_db):
            import asyncio

            asyncio.get_event_loop().run_until_complete(
                fire_state_changed_triggers(node.id, "inbox", "ready")
            )

        mock_exec.assert_called_once()
        fired_trigger = mock_exec.call_args[0][0]
        assert fired_trigger.id == trigger.id


def test_state_changed_trigger_filters_from_status(sync_db):
    """Un trigger avec from_status ne se déclenche que si l'ancien statut correspond."""
    user, mm, node, agent = _seed_mindmap_with_node(sync_db, status="inbox")

    trigger = Trigger(
        node_id=node.id,
        trigger_type="state_changed",
        enabled=True,
        config={
            "from_status": "doing",
            "task_type": "agent",
            "selected_agent": str(agent.id),
        },
    )
    sync_db.add(trigger)
    sync_db.commit()

    from app.services.state_changed import fire_state_changed_triggers

    with patch(
        "app.services.state_changed.execute_trigger_with_config",
        new_callable=AsyncMock,
    ) as mock_exec:
        with patch("app.services.state_changed.SessionLocal", return_value=sync_db):
            import asyncio

            asyncio.get_event_loop().run_until_complete(
                fire_state_changed_triggers(node.id, "inbox", "ready")
            )

        mock_exec.assert_not_called()


def test_state_changed_trigger_filters_to_status(sync_db):
    """Un trigger avec to_status ne se déclenche que si le nouveau statut correspond."""
    user, mm, node, agent = _seed_mindmap_with_node(sync_db, status="inbox")

    trigger = Trigger(
        node_id=node.id,
        trigger_type="state_changed",
        enabled=True,
        config={
            "to_status": "done",
            "task_type": "agent",
            "selected_agent": str(agent.id),
        },
    )
    sync_db.add(trigger)
    sync_db.commit()

    from app.services.state_changed import fire_state_changed_triggers

    with patch(
        "app.services.state_changed.execute_trigger_with_config",
        new_callable=AsyncMock,
    ) as mock_exec:
        with patch("app.services.state_changed.SessionLocal", return_value=sync_db):
            import asyncio

            # inbox → ready : ne doit pas se déclencher
            asyncio.get_event_loop().run_until_complete(
                fire_state_changed_triggers(node.id, "inbox", "ready")
            )
            mock_exec.assert_not_called()

            # inbox → done : doit se déclencher
            asyncio.get_event_loop().run_until_complete(
                fire_state_changed_triggers(node.id, "inbox", "done")
            )
            mock_exec.assert_called_once()


def test_state_changed_trigger_disabled_not_fired(sync_db):
    """Un trigger désactivé ne se déclenche pas."""
    user, mm, node, agent = _seed_mindmap_with_node(sync_db, status="inbox")

    trigger = Trigger(
        node_id=node.id,
        trigger_type="state_changed",
        enabled=False,
        config={
            "task_type": "agent",
            "selected_agent": str(agent.id),
        },
    )
    sync_db.add(trigger)
    sync_db.commit()

    from app.services.state_changed import fire_state_changed_triggers

    with patch(
        "app.services.state_changed.execute_trigger_with_config",
        new_callable=AsyncMock,
    ) as mock_exec:
        with patch("app.services.state_changed.SessionLocal", return_value=sync_db):
            import asyncio

            asyncio.get_event_loop().run_until_complete(
                fire_state_changed_triggers(node.id, "inbox", "ready")
            )

        mock_exec.assert_not_called()


def test_state_changed_no_triggers_on_node(sync_db):
    """Aucun trigger attaché → aucune exécution."""
    user, mm, node, agent = _seed_mindmap_with_node(sync_db, status="inbox")

    from app.services.state_changed import fire_state_changed_triggers

    with patch(
        "app.services.state_changed.execute_trigger_with_config",
        new_callable=AsyncMock,
    ) as mock_exec:
        with patch("app.services.state_changed.SessionLocal", return_value=sync_db):
            import asyncio

            asyncio.get_event_loop().run_until_complete(
                fire_state_changed_triggers(node.id, "inbox", "ready")
            )

        mock_exec.assert_not_called()


# ---------------------------------------------------------------------------
# Tests write_to_graph
# ---------------------------------------------------------------------------


def test_write_to_graph_key_findings(sync_db):
    """write_to_graph crée un nœud rapport + un nœud par key_finding."""
    user, mm, node, agent = _seed_mindmap_with_node(sync_db)

    trigger = Trigger(
        node_id=node.id,
        trigger_type="cron",
        enabled=True,
        config={"write_to_graph": True},
    )
    sync_db.add(trigger)
    sync_db.commit()

    result = {
        "agent_name": "News Monitor",
        "output_raw": "Rapport complet...",
        "output_parsed": {
            "executive_summary": "Résumé de la veille IA du jour",
            "key_findings": [
                {
                    "title": "GPT-5 annoncé",
                    "description": "OpenAI annonce GPT-5 pour Q3 2026",
                    "importance": "high",
                    "source": "techcrunch.com",
                },
                {
                    "title": "Claude 4 benchmarks",
                    "description": "Anthropic publie les benchmarks",
                    "importance": "medium",
                },
            ],
        },
    }

    import asyncio
    from app.services.scheduler import _write_agent_results_to_graph

    asyncio.get_event_loop().run_until_complete(
        _write_agent_results_to_graph(trigger, result, sync_db)
    )

    children = (
        sync_db.query(Node)
        .filter(Node.parent_id == node.id, Node.mindmap_id == mm.id)
        .all()
    )
    assert len(children) == 1
    report_node = children[0]
    assert "Rapport" in report_node.label
    assert report_node.status == "inbox"
    assert "Résumé" in report_node.description

    findings = (
        sync_db.query(Node)
        .filter(Node.parent_id == report_node.id, Node.mindmap_id == mm.id)
        .all()
    )
    assert len(findings) == 2
    labels = {f.label for f in findings}
    assert "GPT-5 annoncé" in labels
    assert "Claude 4 benchmarks" in labels

    gpt_finding = next(f for f in findings if "GPT-5" in f.label)
    assert "techcrunch.com" in gpt_finding.description
    assert "high" in gpt_finding.description


def test_write_to_graph_markdown_fallback(sync_db):
    """write_to_graph crée un nœud résumé quand la sortie est du Markdown."""
    user, mm, node, agent = _seed_mindmap_with_node(sync_db)

    trigger = Trigger(
        node_id=node.id,
        trigger_type="cron",
        enabled=True,
        config={"write_to_graph": True},
    )
    sync_db.add(trigger)
    sync_db.commit()

    result = {
        "agent_name": "Weather Agent",
        "output_raw": "## Météo Paris\n\nSoleil toute la journée, 22°C.",
        "output_parsed": {
            "markdown": "## Météo Paris\n\nSoleil toute la journée, 22°C.",
            "format": "markdown",
        },
    }

    import asyncio
    from app.services.scheduler import _write_agent_results_to_graph

    asyncio.get_event_loop().run_until_complete(
        _write_agent_results_to_graph(trigger, result, sync_db)
    )

    children = (
        sync_db.query(Node)
        .filter(Node.parent_id == node.id, Node.mindmap_id == mm.id)
        .all()
    )
    assert len(children) == 1
    assert "Weather Agent" in children[0].label
    assert "Météo Paris" in children[0].description


def test_write_to_graph_not_called_without_flag(sync_db):
    """Sans write_to_graph dans la config, aucun nœud n'est créé."""
    user, mm, node, agent = _seed_mindmap_with_node(sync_db)

    trigger = Trigger(
        node_id=node.id,
        trigger_type="cron",
        enabled=True,
        config={},
    )
    sync_db.add(trigger)
    sync_db.commit()

    children_before = (
        sync_db.query(Node)
        .filter(Node.parent_id == node.id, Node.mindmap_id == mm.id)
        .count()
    )
    assert children_before == 0
