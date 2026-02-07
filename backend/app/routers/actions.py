import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_async_session
from app.models.action import Action
from app.schemas.action import ActionCreate, ActionListOut, ActionOut, ActionUpdate

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/actions", tags=["actions"], dependencies=[Depends(get_current_user)]
)


@router.get("", response_model=ActionListOut)
async def list_actions(
    node_id: int | None = None, session: AsyncSession = Depends(get_async_session)
) -> ActionListOut:
    logger.info(f"📋 [Actions] list_actions appelé avec node_id: {node_id} (type: {type(node_id).__name__})")
    
    try:
        query = select(Action)
        
        if node_id is not None:
            logger.info(f"📋 [Actions] Filtrage par node_id: {node_id}")
            query = query.where(Action.node_id == node_id)
        else:
            logger.info(f"📋 [Actions] Aucun filtrage node_id, récupération de toutes les actions")
        
        result = await session.execute(query)
        raw_actions = result.scalars().all()
        logger.info(f"📋 [Actions] {len(raw_actions)} action(s) brute(s) trouvée(s) en base")
        
        # Logger les détails de chaque action trouvée
        for idx, action in enumerate(raw_actions):
            logger.info(
                f"📋 [Actions] Action #{idx + 1}: id={action.id}, "
                f"node_id={action.node_id}, trigger_id={action.trigger_id}, "
                f"action_type={action.action_type}, name={action.name}, "
                f"enabled={action.enabled}"
            )
        
        actions = [ActionOut.model_validate(a) for a in raw_actions]
        logger.info(f"📋 [Actions] {len(actions)} action(s) validée(s) et retournée(s)")
        
        # Logger un résumé des actions retournées
        if actions:
            action_summary = [
                {
                    "id": a.id,
                    "node_id": a.node_id,
                    "action_type": a.action_type,
                    "name": a.name,
                    "enabled": a.enabled
                }
                for a in actions
            ]
            logger.info(f"📋 [Actions] Résumé des actions retournées: {action_summary}")
        else:
            logger.info(f"📋 [Actions] Aucune action à retourner")
        
        return ActionListOut(actions=actions)
    except Exception as e:
        logger.error(f"❌ [Actions] Erreur lors de la récupération des actions: {e}", exc_info=True)
        logger.error(f"❌ [Actions] Paramètres de la requête: node_id={node_id}")
        raise


ACTION_TYPE_NAMES = {
    "draft_email": "Préparer l'email",
    "send_email": "Envoyer l'email",
    "call_api": "Appeler une API",
    "update_node": "Mettre à jour le nœud",
    "run_agent": "Exécuter un agent",
    "notify": "Notification",
    "create_reminder": "Créer un rappel",
    "reminder": "Rappel",
}


@router.post("", response_model=ActionOut)
async def create_action(
    payload: ActionCreate, session: AsyncSession = Depends(get_async_session)
) -> ActionOut:
    logger.info(f"➕ [Actions] create_action appelé avec payload: {payload}")
    logger.info(f"➕ [Actions] Détails du payload: {payload.model_dump()}")
    
    try:
        data = payload.model_dump()
        logger.info(f"➕ [Actions] Données extraites du payload: {data}")
        
        # Générer un nom par défaut basé sur le type d'action
        if not data.get("name"):
            action_type_str = data.get("action_type")
            logger.info(f"➕ [Actions] Nom manquant, génération basée sur action_type: {action_type_str}")
            if hasattr(action_type_str, "value"):
                action_type_str = action_type_str.value
                logger.info(f"➕ [Actions] action_type converti en valeur: {action_type_str}")
            data["name"] = ACTION_TYPE_NAMES.get(action_type_str, f"Action {action_type_str}")
            logger.info(f"➕ [Actions] Nom généré: {data['name']}")
        else:
            logger.info(f"➕ [Actions] Nom fourni: {data.get('name')}")
        
        logger.info(f"➕ [Actions] Données finales pour création: {data}")
        action = Action(**data)
        logger.info(f"➕ [Actions] Instance Action créée: node_id={action.node_id}, action_type={action.action_type}, name={action.name}")
        
        session.add(action)
        logger.info(f"➕ [Actions] Action ajoutée à la session")
        
        await session.flush()
        logger.info(f"➕ [Actions] Session flush effectué, action.id={action.id}")
        
        await session.commit()
        logger.info(f"✅ [Actions] Action créée avec succès: id={action.id}, node_id={action.node_id}, action_type={action.action_type}, name={action.name}")
        
        action_out = ActionOut.model_validate(action)
        logger.info(f"✅ [Actions] ActionOut validé: id={action_out.id}, node_id={action_out.node_id}, action_type={action_out.action_type}")
        return action_out
    except Exception as e:
        logger.error(f"❌ [Actions] Erreur lors de la création de l'action: {e}", exc_info=True)
        logger.error(f"❌ [Actions] Payload reçu: {payload.model_dump() if payload else 'None'}")
        raise


@router.patch("/{action_id}", response_model=ActionOut)
async def update_action(
    action_id: int,
    payload: ActionUpdate,
    session: AsyncSession = Depends(get_async_session),
) -> ActionOut:
    action = await session.get(Action, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action introuvable")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(action, field, value)
    await session.commit()
    return ActionOut.model_validate(action)


@router.delete("/{action_id}")
async def delete_action(
    action_id: int, session: AsyncSession = Depends(get_async_session)
) -> dict:
    action = await session.get(Action, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action introuvable")
    await session.delete(action)
    await session.commit()
    return {"deleted": True}
