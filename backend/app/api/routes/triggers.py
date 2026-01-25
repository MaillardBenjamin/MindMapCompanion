from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database import get_db
from app.db.session import get_async_session
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.mindmap import Trigger
from app.models.mindmap import Action
from app.schemas.mindmap import (
    TriggerCreate,
    TriggerUpdate,
    TriggerResponse,
    TriggerWithActions,
)
from app.schemas.trigger_execution import TriggerManualExecuteRequest, TriggerManualExecuteResponse
from app.crud import mindmap as crud_mindmap
from app.services.executor import execute_actions_for_node
from app.services.configurable_agent_service import configurable_agent_service

router = APIRouter(prefix="/api/triggers", tags=["triggers"])


@router.post("", response_model=TriggerResponse, status_code=status.HTTP_201_CREATED)
def create_trigger(
    trigger: TriggerCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Crée un nouveau trigger sur un nœud"""
    db_trigger = crud_mindmap.create_trigger(db, trigger=trigger, user_id=current_user.id)
    if not db_trigger:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nœud introuvable ou vous n'avez pas accès à ce nœud"
        )
    return db_trigger


@router.get("/node/{node_id}", response_model=List[TriggerResponse])
def get_triggers_by_node(
    node_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupère tous les triggers d'un nœud"""
    triggers = crud_mindmap.get_triggers_by_node(db, node_id=node_id, user_id=current_user.id)
    return triggers


@router.get("/{trigger_id}", response_model=TriggerWithActions)
def get_trigger(
    trigger_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupère un trigger avec ses actions"""
    db_trigger = crud_mindmap.get_trigger(db, trigger_id=trigger_id, user_id=current_user.id)
    if not db_trigger:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trigger introuvable"
        )
    
    # Charger les actions
    actions = crud_mindmap.get_actions_by_trigger(
        db, trigger_id=trigger_id, user_id=current_user.id
    )
    db_trigger.actions = actions
    
    return db_trigger


@router.put("/{trigger_id}", response_model=TriggerResponse)
def update_trigger(
    trigger_id: int,
    trigger_update: TriggerUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Met à jour un trigger"""
    db_trigger = crud_mindmap.update_trigger(
        db, trigger_id=trigger_id, user_id=current_user.id, trigger_update=trigger_update
    )
    if not db_trigger:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trigger introuvable"
        )
    return db_trigger


@router.delete("/{trigger_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trigger(
    trigger_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Supprime un trigger (cascade sur les actions)"""
    success = crud_mindmap.delete_trigger(db, trigger_id=trigger_id, user_id=current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trigger introuvable"
        )
    return None


@router.post("/{trigger_id}/execute", response_model=TriggerManualExecuteResponse)
async def execute_trigger_manually(
    trigger_id: str,
    payload: TriggerManualExecuteRequest,
    async_session: AsyncSession = Depends(get_async_session),
    db_sync: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TriggerManualExecuteResponse:
    """
    Lance un trigger manuellement avec une task/agent sélectionnée.
    
    Args:
        trigger_id: ID du trigger à exécuter (Integer en string)
        payload: Configuration de l'exécution (task_type, task_id, output_type, etc.)
    """
    # NOTE: historique de schéma -> certains modèles utilisent encore des IDs entiers (mindmap.py),
    # alors que d'autres tables utilisent des UUID. Ici, `Trigger` provient de `app.models.mindmap`,
    # donc l'ID est un int. On accepte une string côté API pour rester compatible avec le frontend.
    #
    # Si on migre tout en UUID plus tard, cette conversion et les types devront être refactorisés.
    # Convertir trigger_id en int
    try:
        trigger_id_int = int(trigger_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Format d'ID de trigger invalide")
    
    # Récupérer le trigger via crud pour vérifier les permissions
    trigger = crud_mindmap.get_trigger(db_sync, trigger_id_int, current_user.id)
    
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger introuvable")
    
    if not trigger.enabled:
        raise HTTPException(status_code=400, detail="Le trigger est désactivé")
    
    output = None
    email_sent = False
    
    try:
        # Exécuter la task selon le type.
        # IMPORTANT: on garde une session sync (`db_sync`) pour les CRUD historiques,
        # et une session async (`async_session`) pour l'exécuteur d'actions (évite de bloquer).
        if payload.task_type == "agent":
            # Exécuter un agent configurable
            from app.crud.configurable_agent import get_agent_by_id
            
            agent = get_agent_by_id(db_sync, int(payload.task_id), current_user.id)
            if not agent:
                raise HTTPException(status_code=404, detail="Agent configurable introuvable")
            
            # Préparer le texte d'entrée (utiliser la description du nœud si pas fourni)
            input_text = payload.input_text
            if not input_text:
                # Récupérer le nœud associé au trigger pour obtenir son contenu
                from app.models.mindmap import Node
                # Utiliser la session sync car Node utilise Integer pour l'ID (modèle historique mindmap.py)
                node = crud_mindmap.get_node(db_sync, trigger.node_id, current_user.id)
                if node:
                    input_text = node.description or node.label or ""
            
            # Exécuter l'agent
            result = await configurable_agent_service.execute_agent(
                db=db_sync,
                agent_id=agent.id,
                user_id=current_user.id,
                input_text=input_text or "",
                options={},
            )
            
            output = {
                "output_raw": result.get("output_raw"),
                "output_parsed": result.get("output_parsed"),
                "execution_time_ms": result.get("execution_time_ms"),
                "prompt_used": result.get("prompt_used"),
                "input_text": result.get("input_text"),
                "agent_name": result.get("agent_name"),
            }
            
        elif payload.task_type == "action":
            # Exécuter une action
            action = crud_mindmap.get_action(db_sync, int(payload.task_id), current_user.id)
            if not action:
                raise HTTPException(status_code=404, detail="Action introuvable")
            
            # Exécuter les actions du nœud via le service executor
            await execute_actions_for_node(
                session=async_session,
                node_id=str(trigger.node_id),
                trigger_id=str(trigger.id),
            )
            
            output = {"message": "Action exécutée avec succès"}
        
        # Gérer le rendu de sortie
        if payload.output_type == "email" and payload.email_config:
            import logging
            logger = logging.getLogger(__name__)
            
            logger.info(f"📧 [TriggerExecute] Type de rendu: EMAIL")
            logger.info(f"📧 [TriggerExecute] Configuration email: {payload.email_config}")
            
            # Envoyer par email
            from app.services.email_smtp import send_email, format_agent_output_as_email
            
            to_email = payload.email_config.get("to")
            logger.info(f"📧 [TriggerExecute] Destinataire: {to_email}")
            
            # Déterminer le sujet de l'email
            agent_name_for_subject = None
            if payload.task_type == "agent":
                agent_name_for_subject = agent.name if 'agent' in locals() else "inconnu"
            email_subject = payload.email_config.get("subject") or f"Résultat de l'agent {agent_name_for_subject}" if agent_name_for_subject else "Résultat de l'exécution"
            logger.info(f"📧 [TriggerExecute] Sujet de l'email: {email_subject}")
            
            if not to_email:
                logger.error(f"❌ [TriggerExecute] Adresse email du destinataire manquante")
                raise HTTPException(status_code=400, detail="L'adresse email du destinataire est requise")
            
            # Formater le contenu de l'email
            logger.info(f"📧 [TriggerExecute] Formatage du contenu de l'email...")
            if payload.task_type == "agent" and output:
                logger.info(f"📧 [TriggerExecute] Type: Agent - Formatage de la sortie")
                body_text, body_html = format_agent_output_as_email(
                    output_raw=output.get("output_raw", ""),
                    output_parsed=output.get("output_parsed"),
                    agent_name=agent.name if 'agent' in locals() else None,
                    input_text=input_text if 'input_text' in locals() else None,
                    execution_time_ms=output.get("execution_time_ms"),
                )
            else:
                logger.info(f"📧 [TriggerExecute] Type: Action - Message simple")
                # Pour les actions, créer un message simple
                body_text = output.get("message", "Action exécutée avec succès") if output else "Action exécutée avec succès"
                body_html = f"<html><body><p>{body_text}</p></body></html>"
            
            logger.info(f"📧 [TriggerExecute] Contenu formaté - Texte: {len(body_text)} caractères, HTML: {len(body_html)} caractères")
            
            # Envoyer l'email
            logger.info(f"📧 [TriggerExecute] Appel de send_email()...")
            email_sent = send_email(
                to_email=to_email,
                subject=email_subject,
                body_text=body_text,
                body_html=body_html,
            )
            
            if not email_sent:
                logger.error(f"❌ [TriggerExecute] Échec de l'envoi de l'email")
                raise HTTPException(status_code=500, detail="Erreur lors de l'envoi de l'email")
            
            logger.info(f"✅ [TriggerExecute] Email envoyé avec succès")
        
        return TriggerManualExecuteResponse(
            success=True,
            message="Trigger exécuté avec succès",
            execution_id=str(trigger_id),
            output=output,
            email_sent=email_sent if payload.output_type == "email" else None,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'exécution du trigger: {str(e)}"
        )
