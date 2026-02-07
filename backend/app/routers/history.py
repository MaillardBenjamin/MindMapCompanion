from datetime import datetime
from typing import Optional
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_async_session
from app.database import get_db
from app.models.user import User
from app.models.execution_log import ExecutionLog
from app.models.configurable_agent import AgentExecutionLog
from app.models.event import Event
from app.models.mindmap import Node, Trigger, Action, Mindmap
from app.schemas.history import HistoryItemOut, HistoryListOut
from app.crud.configurable_agent import get_agent_by_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/history", tags=["history"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=HistoryListOut)
async def get_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    node_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    async_session: AsyncSession = Depends(get_async_session),
    db: Session = Depends(get_db),
) -> HistoryListOut:
    """
    Récupère l'historique unifié de toutes les activités :
    - Exécutions d'agents
    - Exécutions de triggers/actions
    - Événements système
    - Créations/modifications de nœuds, triggers, actions
    """
    items: list[HistoryItemOut] = []
    
    # Récupérer les mindmaps de l'utilisateur une seule fois
    user_mindmaps = db.query(Mindmap).filter(Mindmap.user_id == current_user.id).all()
    mindmap_ids = [m.id for m in user_mindmaps]
    
    # 1. Récupérer les exécutions d'agents
    try:
        agent_logs_query = select(AgentExecutionLog).where(
            AgentExecutionLog.user_id == current_user.id
        ).order_by(desc(AgentExecutionLog.created_at))
        
        agent_logs_result = await async_session.execute(agent_logs_query)
        agent_logs = agent_logs_result.scalars().all()
        
        for log in agent_logs:
            try:
                agent = get_agent_by_id(db, log.agent_id, current_user.id)
                items.append(HistoryItemOut(
                    id=f"agent_exec_{log.id}",
                    type="agent_execution",
                    created_at=log.created_at,
                    title=f"Exécution de l'agent {agent.name if agent else 'inconnu'}",
                    description=log.input_text[:200] if log.input_text else None,
                    status="success" if log.success else "failed",
                    agent_id=log.agent_id,
                    agent_name=agent.name if agent else None,
                    metadata={
                        "execution_time_ms": log.execution_time_ms,
                        "error_message": log.error_message,
                    }
                ))
            except Exception as e:
                logger.warning(f"Erreur lors de la récupération de l'agent {log.agent_id}: {e}")
                items.append(HistoryItemOut(
                    id=f"agent_exec_{log.id}",
                    type="agent_execution",
                    created_at=log.created_at,
                    title="Exécution d'agent",
                    description=log.input_text[:200] if log.input_text else None,
                    status="success" if log.success else "failed",
                    agent_id=log.agent_id,
                    agent_name=None,
                    metadata={
                        "execution_time_ms": log.execution_time_ms,
                        "error_message": log.error_message,
                    }
                ))
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des logs d'agents: {e}")
    
    # 2. Récupérer les exécutions de triggers/actions (ExecutionLog)
    try:
        exec_logs_query = select(ExecutionLog).order_by(desc(ExecutionLog.created_at))
        
        if node_id:
            exec_logs_query = exec_logs_query.where(ExecutionLog.node_id == node_id)
        
        exec_logs_result = await async_session.execute(exec_logs_query)
        exec_logs = exec_logs_result.scalars().all()
        
        for log in exec_logs:
            try:
                # Récupérer les informations du nœud si disponible
                node_label = None
                if log.node_id:
                    node = db.query(Node).filter(Node.id == log.node_id).first()
                    if node:
                        # Vérifier que le nœud appartient à l'utilisateur
                        if node.mindmap_id in mindmap_ids:
                            node_label = node.label
                
                # Déterminer le type et le titre
                if log.trigger_id:
                    trigger = db.query(Trigger).filter(Trigger.id == log.trigger_id).first()
                    trigger_type = trigger.trigger_type if trigger else "inconnu"
                    
                    items.append(HistoryItemOut(
                        id=f"trigger_exec_{log.id}",
                        type="trigger_execution",
                        created_at=log.created_at,
                        title=f"Exécution du trigger {trigger_type}",
                        description=f"Sur le nœud: {node_label}" if node_label else None,
                        status=log.status.value if log.status else None,
                        node_id=log.node_id,
                        node_label=node_label,
                        trigger_id=log.trigger_id,
                        metadata={
                            "input_snapshot": log.input_snapshot,
                            "output_snapshot": log.output_snapshot,
                            "error_message": log.error_message,
                        }
                    ))
                elif log.action_id:
                    action = db.query(Action).filter(Action.id == log.action_id).first()
                    action_type = (getattr(action, "action_type", None) or getattr(action, "type", None)) if action else "inconnu"
                    
                    items.append(HistoryItemOut(
                        id=f"action_exec_{log.id}",
                        type="action_execution",
                        created_at=log.created_at,
                        title=f"Exécution de l'action {action_type}",
                        description=f"Sur le nœud: {node_label}" if node_label else None,
                        status=log.status.value if log.status else None,
                        node_id=log.node_id,
                        node_label=node_label,
                        action_id=log.action_id,
                        metadata={
                            "input_snapshot": log.input_snapshot,
                            "output_snapshot": log.output_snapshot,
                            "error_message": log.error_message,
                        }
                    ))
            except Exception as e:
                logger.warning(f"Erreur lors du traitement d'un ExecutionLog {log.id}: {e}")
                continue
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des ExecutionLog: {e}")
    
    # 3. Récupérer les événements système
    try:
        events_query = select(Event).order_by(desc(Event.created_at))
        events_result = await async_session.execute(events_query)
        events = events_result.scalars().all()
        
        for event in events:
            try:
                event_type_label = {
                    "TextIngested": "Texte ingéré",
                    "EmailReceived": "Email reçu",
                    "DateReached": "Date atteinte",
                    "CronTick": "Tâche planifiée",
                    "NodeStateChanged": "État du nœud modifié",
                }.get(event.event_type.value, event.event_type.value)
                
                items.append(HistoryItemOut(
                    id=f"event_{event.id}",
                    type="event",
                    created_at=event.created_at,
                    title=event_type_label,
                    description=str(event.payload),
                    metadata={"payload": event.payload}
                ))
            except Exception as e:
                logger.warning(f"Erreur lors du traitement d'un Event {event.id}: {e}")
                continue
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des Events: {e}")
    
    # 4. Récupérer les créations/modifications de nœuds (via created_at)
    try:
        if mindmap_ids:
            nodes_query = db.query(Node).filter(Node.mindmap_id.in_(mindmap_ids)).order_by(desc(Node.created_at))
            if node_id:
                nodes_query = nodes_query.filter(Node.id == node_id)
            
            nodes = nodes_query.limit(100).all()
            
            for node in nodes:
                try:
                    # Création du nœud
                    items.append(HistoryItemOut(
                        id=f"node_created_{node.id}",
                        type="node_created",
                        created_at=node.created_at,
                        title=f"Nœud créé: {node.label}",
                        description=node.description,
                        node_id=node.id,
                        node_label=node.label,
                        metadata={"status": node.status}
                    ))
                    
                    # Modification du nœud (si updated_at > created_at)
                    if node.updated_at and node.updated_at > node.created_at:
                        items.append(HistoryItemOut(
                            id=f"node_updated_{node.id}_{int(node.updated_at.timestamp())}",
                            type="node_updated",
                            created_at=node.updated_at,
                            title=f"Nœud modifié: {node.label}",
                            description=node.description,
                            node_id=node.id,
                            node_label=node.label,
                            metadata={"status": node.status}
                        ))
                except Exception as e:
                    logger.warning(f"Erreur lors du traitement d'un Node {node.id}: {e}")
                    continue
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des Nodes: {e}")
    
    # 5. Récupérer les créations/modifications d'actions
    try:
        if mindmap_ids:
            # Récupérer les triggers des nœuds de l'utilisateur
            try:
                user_triggers = db.query(Trigger).join(Node).filter(Node.mindmap_id.in_(mindmap_ids)).all()
                trigger_ids = [t.id for t in user_triggers]
                
                if trigger_ids:
                    # Utiliser order_by seulement si created_at existe
                    try:
                        actions = db.query(Action).filter(Action.trigger_id.in_(trigger_ids)).order_by(desc(Action.created_at)).limit(100).all()
                    except Exception as e:
                        logger.warning(f"Erreur lors de l'ordre par created_at, tentative sans ordre: {e}")
                        actions = db.query(Action).filter(Action.trigger_id.in_(trigger_ids)).limit(100).all()
                    
                    for action in actions:
                        try:
                            # Récupérer le nœud via le trigger
                            trigger = db.query(Trigger).filter(Trigger.id == action.trigger_id).first()
                            action_node = None
                            if trigger:
                                action_node = db.query(Node).filter(Node.id == trigger.node_id).first()
                            
                            # Utiliser created_at si disponible, sinon utiliser une date par défaut
                            action_created_at = action.created_at if hasattr(action, 'created_at') and action.created_at else datetime.now()
                            
                            items.append(HistoryItemOut(
                                id=f"action_created_{action.id}",
                                type="action_created",
                                created_at=action_created_at,
                                title=f"Action créée: {getattr(action, 'action_type', None) or getattr(action, 'type', None)}",
                                description=f"Sur le nœud: {action_node.label if action_node else 'inconnu'}",
                                node_id=action_node.id if action_node else None,
                                node_label=action_node.label if action_node else None,
                                action_id=action.id,
                                trigger_id=action.trigger_id,
                                metadata={"action_type": getattr(action, 'action_type', None) or getattr(action, 'type', None)}
                            ))
                        except Exception as e:
                            logger.warning(f"Erreur lors du traitement d'une Action {action.id}: {e}")
                            continue
            except Exception as e:
                logger.warning(f"Erreur lors de la récupération des triggers pour les actions: {e}")
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des Actions: {e}")
    
    # Trier par date décroissante et appliquer pagination
    items.sort(key=lambda x: x.created_at, reverse=True)
    total = len(items)
    paginated_items = items[skip:skip + limit]
    
    return HistoryListOut(items=paginated_items, total=total)
