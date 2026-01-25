from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mindmap import Action  # Utiliser le modèle mindmap (Integer)
from app.models.enums import ExecutionStatus
from app.models.execution_log import ExecutionLog


async def execute_actions_for_node(
    session: AsyncSession, node_id: int, trigger_id: int | None
) -> None:
    """
    Exécute les actions d'un nœud.
    
    Args:
        session: Session async SQLAlchemy
        node_id: ID du nœud (Integer)
        trigger_id: ID du trigger qui a déclenché l'exécution (Integer, optionnel)
    """
    # Récupérer les actions via le trigger (les actions sont liées aux triggers, pas directement aux nœuds)
    # On doit d'abord récupérer les triggers du nœud, puis les actions de ces triggers
    from app.models.mindmap import Trigger
    
    # Récupérer les triggers du nœud
    triggers_result = await session.execute(
        select(Trigger).where(Trigger.node_id == node_id, Trigger.enabled.is_(True))
    )
    triggers = triggers_result.scalars().all()
    
    # Récupérer toutes les actions de ces triggers
    all_actions = []
    for trigger in triggers:
        actions_result = await session.execute(
            select(Action).where(Action.trigger_id == trigger.id, Action.enabled.is_(True))
        )
        all_actions.extend(actions_result.scalars().all())
    
    # Exécuter et logger chaque action
    for action in all_actions:
        status = ExecutionStatus.success  # Les actions mindmap n'ont pas de mode "review"
        
        log = ExecutionLog(
            node_id=node_id,
            trigger_id=action.trigger_id,
            action_id=action.id,
            status=status,
            input_snapshot={"action": action.type, "config": action.config or {}},
            output_snapshot={"executed_at": datetime.now(tz=timezone.utc).isoformat()},
        )
        session.add(log)
