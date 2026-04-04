"""
Service pour déclencher les triggers state_changed lors d'un changement de statut de nœud.

Quand un nœud du mindmap change de statut (ex: inbox → ready), ce service recherche
les triggers de type state_changed attachés à ce nœud et les exécute via le scheduler.
"""

import logging

from app.models.mindmap import Trigger

logger = logging.getLogger(__name__)


async def fire_state_changed_triggers(
    node_id: int, old_status: str, new_status: str
) -> None:
    """
    Recherche et exécute les triggers state_changed activés pour un nœud.

    Les triggers peuvent filtrer via leur config JSON :
    - from_status : ne se déclenche que si l'ancien statut correspond
    - to_status   : ne se déclenche que si le nouveau statut correspond
    - Si aucun filtre, le trigger se déclenche sur tout changement de statut.
    """
    from app.database import SessionLocal
    from app.services.scheduler import execute_trigger_with_config

    db = SessionLocal()
    try:
        triggers = (
            db.query(Trigger)
            .filter(
                Trigger.node_id == node_id,
                Trigger.enabled == True,
                Trigger.trigger_type == "state_changed",
            )
            .all()
        )

        if not triggers:
            return

        for trigger in triggers:
            config = trigger.config or {}
            from_status = config.get("from_status")
            to_status = config.get("to_status")

            if from_status and from_status != old_status:
                logger.debug(
                    "[StateChanged] Trigger %d ignoré : from_status %s != %s",
                    trigger.id,
                    from_status,
                    old_status,
                )
                continue
            if to_status and to_status != new_status:
                logger.debug(
                    "[StateChanged] Trigger %d ignoré : to_status %s != %s",
                    trigger.id,
                    to_status,
                    new_status,
                )
                continue

            logger.info(
                "🔄 [StateChanged] Déclenchement du trigger %d pour le nœud %d : %s → %s",
                trigger.id,
                node_id,
                old_status,
                new_status,
            )
            await execute_trigger_with_config(trigger)

    except Exception as e:
        logger.error(
            "❌ [StateChanged] Erreur lors du déclenchement des triggers pour le nœud %d : %s",
            node_id,
            e,
            exc_info=True,
        )
    finally:
        db.close()
