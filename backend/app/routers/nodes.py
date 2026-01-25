from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.db.session import get_async_session
from app.models.enums import EventType, TriggerType
from app.models.node import Node
from app.models.trigger import Trigger
from app.schemas.node import NodeOut, NodeUpdate
from app.services.events import get_or_create_event

settings = get_settings()

router = APIRouter(prefix="/nodes", tags=["nodes"], dependencies=[Depends(get_current_user)])


@router.get("/{node_id}", response_model=NodeOut)
async def get_node(node_id: str, session: AsyncSession = Depends(get_async_session)) -> NodeOut:
    node = await session.get(Node, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node introuvable")
    return NodeOut.model_validate(node)


@router.patch("/{node_id}", response_model=NodeOut)
async def update_node(
    node_id: str, payload: NodeUpdate, session: AsyncSession = Depends(get_async_session)
) -> NodeOut:
    node = await session.get(Node, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node introuvable")

    original_status = node.status
    
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(node, field, value)
    await session.flush()

    if payload.status and payload.status != original_status:
        await get_or_create_event(
            session,
            EventType.node_state_changed,
            f"node_state:{node_id}:{payload.status}",
            {"node_id": node_id, "from": original_status, "to": payload.status},
        )

    # Gérer les triggers d'échéance
    if "due_date" in payload.model_dump(exclude_unset=True):
        new_due_date = payload.due_date
        
        # Chercher un trigger existant pour cette échéance
        result = await session.execute(
            select(Trigger).where(
                Trigger.node_id == node.id,
                Trigger.trigger_type == TriggerType.date_reached,
                Trigger.dedupe_key == "due_date"
            )
        )
        existing_trigger = result.scalar_one_or_none()
        
        if new_due_date:
            # Créer ou mettre à jour le trigger
            if existing_trigger:
                # Mettre à jour le trigger existant
                existing_trigger.config = {
                    "run_at": new_due_date.isoformat(),
                    "output_type": "email",
                    "email_to": settings.imap_user,  # Utiliser l'email configuré
                    "email_subject": f"Échéance: {node.title or node.raw_text[:50]}"
                }
                existing_trigger.enabled = True
                existing_trigger.last_fired_at = None  # Réinitialiser pour permettre un nouveau déclenchement
            else:
                # Créer un nouveau trigger
                trigger = Trigger(
                    node_id=node.id,
                    trigger_type=TriggerType.date_reached,
                    config={
                        "run_at": new_due_date.isoformat(),
                        "output_type": "email",
                        "email_to": settings.imap_user,
                        "email_subject": f"Échéance: {node.title or node.raw_text[:50]}"
                    },
                    enabled=True,
                    dedupe_key="due_date"
                )
                session.add(trigger)
        else:
            # Supprimer le trigger si la due_date est supprimée
            if existing_trigger:
                await session.delete(existing_trigger)

    await session.commit()
    return NodeOut.model_validate(node)
