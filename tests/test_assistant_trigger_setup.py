"""
Tests d'intégration : triggers automatiques après génération Assistant IA (feuilles + LLM).
Requiert PostgreSQL (TEST_DATABASE_URL ou URL sync dérivée).
"""

import os
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.auth.password import get_password_hash
from app.database import Base
from app.models.configurable_agent import ConfigurableAgent
from app.models.mindmap import Mindmap, Node, Trigger
from app.models.user import User
from app.services import assistant_trigger_setup as ats
from app.crud import mindmap as mindmap_crud


def _sync_database_url() -> str:
    url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/personal_assistant_test",
    )
    if "+asyncpg" in url:
        return url.replace("+asyncpg", "")
    return url


@pytest.fixture
def sync_db_session():
    url = _sync_database_url()
    engine = create_engine(url, echo=False)
    try:
        conn = engine.connect()
        conn.close()
    except OperationalError as e:
        pytest.skip(f"Base PostgreSQL indisponible ({url}): {e}")

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_find_leaf_node_ids_single():
    assert ats.find_leaf_node_ids([{"id": 1, "label": "a", "parent_id": None}]) == [1]


def test_find_leaf_node_ids_tree():
    created = [
        {"id": 10, "label": "root", "parent_id": None},
        {"id": 11, "label": "mid", "parent_id": 10},
        {"id": 12, "label": "leaf", "parent_id": 11},
    ]
    assert ats.find_leaf_node_ids(created) == [12]


def test_parse_recurring_schedule_lundi_7h():
    s = ats.parse_recurring_schedule_french(
        "Je veux un agent de veille qui s'exécute tous les lundi à 7h sur la bourse"
    )
    assert s is not None
    assert s["cron_days"] == [1]
    assert s["cron_hour"] == 7
    assert s["cron_minute"] == 0


def test_parse_recurring_schedule_7h30_multiple_days():
    s = ats.parse_recurring_schedule_french("rappel mardi et jeudi à 7h30")
    assert s is not None
    assert s["cron_days"] == [2, 4]
    assert s["cron_hour"] == 7
    assert s["cron_minute"] == 30


def test_parse_recurring_schedule_none_without_cues():
    assert ats.parse_recurring_schedule_french("organiser mes idées sans horaire") is None


def test_leaf_matches_cron_context():
    assert ats.leaf_matches_cron_context("Agent de veille — lun 07:00", "Automatisé") is True
    assert ats.leaf_matches_cron_context("Répercussions sur la bourse", "Impact climat") is False


def test_looks_like_schedule_only_node():
    assert ats._looks_like_schedule_only_node("Hebdo : lun 07h", "Planification") is True
    assert ats._looks_like_schedule_only_node(
        "Veille climat & bourse", "Tous les lundis à 7h, sujets climat et marchés"
    ) is False


def test_find_leaf_node_ids_two_leaves():
    created = [
        {"id": 1, "label": "p", "parent_id": None},
        {"id": 2, "label": "a", "parent_id": 1},
        {"id": 3, "label": "b", "parent_id": 1},
    ]
    leaves = set(ats.find_leaf_node_ids(created))
    assert leaves == {2, 3}


def _seed_user_mindmap_tree(sync_db_session):
    user = User(
        email="assistant-trigger-test@example.com",
        hashed_password=get_password_hash("secret"),
        is_active=True,
    )
    sync_db_session.add(user)
    sync_db_session.flush()

    mm = Mindmap(user_id=user.id, name="Test MM", description=None)
    sync_db_session.add(mm)
    sync_db_session.flush()

    root = Node(
        mindmap_id=mm.id,
        parent_id=None,
        label="Racine",
        description="",
        color="#00D9FF",
        position_x=0,
        position_y=0,
        is_root=True,
        status="idle",
    )
    sync_db_session.add(root)
    sync_db_session.flush()

    parent = Node(
        mindmap_id=mm.id,
        parent_id=root.id,
        label="Theme",
        description="Contexte theme",
        color="#00D9FF",
        position_x=200,
        position_y=0,
        is_root=False,
        status="idle",
    )
    sync_db_session.add(parent)
    sync_db_session.flush()

    leaf_a = Node(
        mindmap_id=mm.id,
        parent_id=parent.id,
        label="Tache A",
        description="Envoyer un email",
        color="#00D9FF",
        position_x=400,
        position_y=0,
        is_root=False,
        status="idle",
    )
    leaf_b = Node(
        mindmap_id=mm.id,
        parent_id=parent.id,
        label="Tache B",
        description="Autre",
        color="#00D9FF",
        position_x=400,
        position_y=80,
        is_root=False,
        status="idle",
    )
    sync_db_session.add_all([leaf_a, leaf_b])
    sync_db_session.flush()

    agent = ConfigurableAgent(
        user_id=user.id,
        name="Agent Email",
        slug="agent-email-trigger-test",
        description="Redige et envoie des emails professionnels",
        markdown_config="# Agent\n",
        prompt_template="{{input_text}}",
        is_active=True,
        is_public=False,
    )
    sync_db_session.add(agent)
    sync_db_session.commit()

    created_nodes = [
        {"id": parent.id, "label": parent.label, "parent_id": parent.parent_id},
        {"id": leaf_a.id, "label": leaf_a.label, "parent_id": leaf_a.parent_id},
        {"id": leaf_b.id, "label": leaf_b.label, "parent_id": leaf_b.parent_id},
    ]
    existing_nodes = [root, parent, leaf_a, leaf_b]
    return user, created_nodes, existing_nodes, agent, parent.id


def test_auto_triggers_leaves_when_llm_picks_agent(sync_db_session):
    user, created_nodes, existing_nodes, agent, parent_id = _seed_user_mindmap_tree(
        sync_db_session
    )

    def fake_llm(_prompt: str):
        return {"agent_id": agent.id, "reasoning": "adapté email"}

    with patch.object(ats, "_run_agent_choice_llm", side_effect=fake_llm):
        out = ats.auto_create_triggers_for_leaves(
            sync_db_session,
            user_id=user.id,
            user_text="Preparer des emails pour le projet",
            created_nodes=created_nodes,
            existing_nodes=existing_nodes,
        )

    assert len(out) == 2
    leaf_ids = {r["node_id"] for r in out}
    assert parent_id not in leaf_ids

    for row in out:
        assert row["agent_id"] == agent.id
        t = (
            sync_db_session.query(Trigger)
            .filter(Trigger.id == row["trigger_id"])
            .first()
        )
        assert t is not None
        assert t.trigger_type == "manual"
        assert t.config.get("task_type") == "agent"
        assert t.config.get("selected_agent") == str(agent.id)
        assert t.config.get("output_type") == "mindmap_child"


def test_mixed_cron_on_veille_leaf_manual_on_other(sync_db_session):
    """Planif + plusieurs feuilles : un seul trigger (cron) sur le nœud le plus aligné avec le texte."""
    user, created_nodes, existing_nodes, agent, _parent_id = _seed_user_mindmap_tree(
        sync_db_session
    )
    new_created = []
    for c in created_nodes:
        nc = dict(c)
        if c["label"] == "Tache A":
            nc["label"] = "Agent de veille — lun 07:00"
        elif c["label"] == "Tache B":
            nc["label"] = "Répercussions sur la bourse"
        new_created.append(nc)

    def fake_llm(_prompt: str):
        return {"agent_id": agent.id, "reasoning": "ok"}

    with patch.object(ats, "_run_agent_choice_llm", side_effect=fake_llm):
        out = ats.auto_create_triggers_for_leaves(
            sync_db_session,
            user_id=user.id,
            user_text="Je veux un agent de veille tous les lundi à 7h",
            created_nodes=new_created,
            existing_nodes=existing_nodes,
        )

    assert len(out) == 1
    id_veille = next(c["id"] for c in new_created if "veille" in c["label"].lower())
    assert out[0]["node_id"] == id_veille
    t_veille = (
        sync_db_session.query(Trigger).filter(Trigger.node_id == id_veille).one()
    )
    assert t_veille.trigger_type == "cron"
    assert t_veille.config.get("output_type") == "mindmap_child"
    assert t_veille.config.get("cron_days") == [1]
    assert t_veille.config.get("cron_hour") == 7
    assert t_veille.config.get("cron_minute") == 0
    assert t_veille.config.get("cron_expression")
    assert sync_db_session.query(Trigger).count() == 1


def test_auto_triggers_none_when_llm_returns_null(sync_db_session):
    user, created_nodes, existing_nodes, _agent, _parent_id = _seed_user_mindmap_tree(
        sync_db_session
    )

    with patch.object(
        ats, "_run_agent_choice_llm", return_value={"agent_id": None, "reasoning": "rien"}
    ):
        out = ats.auto_create_triggers_for_leaves(
            sync_db_session,
            user_id=user.id,
            user_text="x",
            created_nodes=created_nodes,
            existing_nodes=existing_nodes,
        )

    assert out == []
    assert sync_db_session.query(Trigger).count() == 0


def test_no_agents_skips_llm(sync_db_session):
    user = User(
        email="no-agent@example.com",
        hashed_password=get_password_hash("secret"),
        is_active=True,
    )
    sync_db_session.add(user)
    sync_db_session.flush()
    mm = Mindmap(user_id=user.id, name="M", description=None)
    sync_db_session.add(mm)
    sync_db_session.flush()
    n = Node(
        mindmap_id=mm.id,
        parent_id=None,
        label="L",
        description="",
        color="#00D9FF",
        position_x=0,
        position_y=0,
        is_root=True,
        status="idle",
    )
    sync_db_session.add(n)
    sync_db_session.commit()

    created_nodes = [{"id": n.id, "label": n.label, "parent_id": n.parent_id}]
    with patch.object(ats, "_run_agent_choice_llm") as m_llm:
        out = ats.auto_create_triggers_for_leaves(
            sync_db_session,
            user_id=user.id,
            user_text="t",
            created_nodes=created_nodes,
            existing_nodes=[n],
        )
    m_llm.assert_not_called()
    assert out == []


def test_resilience_one_leaf_failure_continues(sync_db_session):
    user, created_nodes, existing_nodes, agent, _parent_id = _seed_user_mindmap_tree(
        sync_db_session
    )

    leaf_entries = [c for c in created_nodes if c["label"] != "Theme"]
    assert len(leaf_entries) == 2
    first_leaf = leaf_entries[0]["id"]

    def fake_llm(_p):
        return {"agent_id": agent.id, "reasoning": "ok"}

    calls = []

    def flaky_create(db, trigger, user_id):
        calls.append(trigger.node_id)
        if trigger.node_id == first_leaf:
            raise RuntimeError("simulated failure")
        return mindmap_crud.create_trigger(db, trigger, user_id)

    with patch.object(ats, "_run_agent_choice_llm", side_effect=fake_llm):
        with patch.object(ats, "create_trigger", side_effect=flaky_create):
            out = ats.auto_create_triggers_for_leaves(
                sync_db_session,
                user_id=user.id,
                user_text="emails",
                created_nodes=created_nodes,
                existing_nodes=existing_nodes,
            )

    assert len(out) == 1
    assert out[0]["node_id"] != first_leaf
    assert sync_db_session.query(Trigger).count() == 1
