import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mindmap import Action, Node, Trigger  # Utiliser le modèle mindmap (Integer)
from app.models.enums import ActionType, ExecutionStatus
from app.models.execution_log import ExecutionLog

logger = logging.getLogger(__name__)


def format_draft_email_from_node(node: Node, action_config: dict) -> tuple[str, str]:
    """
    Prépare le texte d'un email à partir des informations d'un nœud.
    
    Args:
        node: Instance Node (mindmap) pour lequel préparer l'email
        action_config: Configuration de l'action "draft_email" (peut contenir un template personnalisé)
    
    Returns:
        Tuple (body_text, body_html) avec le contenu formaté de l'email
    """
    # Récupérer le template personnalisé si fourni, sinon utiliser le template par défaut
    template = action_config.get("template", "default")
    custom_template = action_config.get("custom_template")
    
    # Si un template personnalisé est fourni, l'utiliser
    if custom_template:
        # Remplacer les variables dans le template
        body_text = custom_template.get("text", "").format(
            label=node.label or "Sans titre",
            description=node.description or "",
            status=node.status or "idle",
        )
        body_html = custom_template.get("html", "").format(
            label=node.label or "Sans titre",
            description=node.description or "",
            status=node.status or "idle",
        )
        return body_text, body_html
    
    # Template par défaut
    body_text = f"{node.label or 'Sans titre'}\n\n"
    if node.description:
        body_text += f"{node.description}\n\n"
    if node.status:
        body_text += f"Statut: {node.status}\n"
    
    # Corps HTML
    html_parts = [
        "<html><body style='font-family: Arial, sans-serif; line-height: 1.6; color: #333;'>",
        f"<h2 style='color: #00D9FF;'>{node.label or 'Sans titre'}</h2>",
    ]
    if node.description:
        html_parts.append(f"<div style='background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;'>")
        html_parts.append(f"<p>{node.description.replace(chr(10), '<br>')}</p>")
        html_parts.append("</div>")
    if node.status:
        html_parts.append(f"<p><strong>Statut:</strong> {node.status}</p>")
    html_parts.extend([
        "</body></html>"
    ])
    body_html = "\n".join(html_parts)
    
    return body_text, body_html


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
    # Récupérer le nœud
    node = await session.get(Node, node_id)
    if not node:
        logger.error(f"❌ [Executor] Nœud {node_id} introuvable")
        return
    
    # Récupérer les actions via le trigger (les actions sont liées aux triggers, pas directement aux nœuds)
    # Si trigger_id est fourni, on ne récupère que les actions de ce trigger spécifique
    # Sinon, on récupère toutes les actions de tous les triggers du nœud
    all_actions = []
    
    if trigger_id:
        # Normaliser trigger_id (le scheduler passe parfois une string)
        try:
            trigger_id_value = int(trigger_id)
        except (TypeError, ValueError):
            trigger_id_value = trigger_id

        # Récupérer le trigger pour accéder à sa config
        trigger = await session.get(Trigger, trigger_id_value)
        trigger_config = trigger.config if trigger else {}

        # Récupérer uniquement les actions du trigger spécifié
        actions_result = await session.execute(
            select(Action).where(Action.trigger_id == trigger_id_value, Action.enabled.is_(True))
        )
        all_actions = actions_result.scalars().all()
        logger.info(
            "🧭 [Executor] Actions trouvées pour trigger_id=%s: %d",
            trigger_id_value,
            len(all_actions),
        )

        # Fallback: si aucune action liée au trigger, utiliser l'action sélectionnée dans la config
        if not all_actions and trigger_config:
            selected_action_id = trigger_config.get("selected_action") or trigger_config.get("task_id")
            try:
                selected_action_id = int(selected_action_id) if selected_action_id is not None else None
            except (TypeError, ValueError):
                selected_action_id = None

            if selected_action_id:
                fallback_result = await session.execute(
                    select(Action).where(Action.id == selected_action_id, Action.enabled.is_(True))
                )
                all_actions = fallback_result.scalars().all()
                logger.info(
                    "🧭 [Executor] Fallback actions via selected_action_id=%s: %d",
                    selected_action_id,
                    len(all_actions),
                )
    else:
        # Récupérer tous les triggers du nœud, puis leurs actions
        triggers_result = await session.execute(
            select(Trigger).where(Trigger.node_id == node_id, Trigger.enabled.is_(True))
        )
        triggers = triggers_result.scalars().all()
        
        for trigger in triggers:
            actions_result = await session.execute(
                select(Action).where(Action.trigger_id == trigger.id, Action.enabled.is_(True))
            )
            all_actions.extend(actions_result.scalars().all())
        
        # Pour le output_type, on prend le premier trigger trouvé (ou None si aucun)
        trigger = triggers[0] if triggers else None
        trigger_config = trigger.config if trigger else {}
    
    # Récupérer la config du trigger pour le output_type et email_to
    output_type = trigger_config.get("output_type", "screen")
    email_to = trigger_config.get("email_to")
    logger.info(
        "📧 [Executor] Trigger config: output_type=%s, email_to=%s, email_subject=%s",
        output_type,
        email_to,
        trigger_config.get("email_subject"),
    )
    
    # Exécuter chaque action selon son type
    for action in all_actions:
        # Compat: certains anciens modèles/records utilisent `type`, le schéma actuel utilise `action_type`.
        action_type = getattr(action, "action_type", None) or getattr(action, "type", None)
        logger.info(
            "🧭 [Executor] Action détectée: id=%s, name=%s, action_type=%s, enabled=%s",
            getattr(action, "id", None),
            action.name,
            action_type,
            getattr(action, "enabled", None),
        )
        action_config = action.config or {}
        status = ExecutionStatus.success
        output_result = {}
        
        try:
            logger.info(f"🔄 [Executor] Exécution de l'action {action.name} (type: {action_type}) pour le nœud {node_id}")
            
            if action_type == ActionType.draft_email.value:
                # Préparer le texte de l'email à partir des infos du nœud
                logger.info(
                    "📝 [Executor] Préparation email: node_id=%s, label=%s, action_config_keys=%s",
                    node_id,
                    getattr(node, "label", None),
                    list(action_config.keys()),
                )
                body_text, body_html = format_draft_email_from_node(node, action_config)
                logger.info(
                    "📝 [Executor] Email préparé: body_text=%d chars, body_html=%d chars",
                    len(body_text),
                    len(body_html),
                )
                output_result = {
                    "body_text": body_text,
                    "body_html": body_html,
                    "prepared_at": datetime.now(tz=timezone.utc).isoformat()
                }
                logger.info(f"✅ [Executor] Email préparé pour l'action {action.name}")
                
                # Si le type de rendu est "email", envoyer l'email
                if output_type == "email" and email_to:
                    from app.services.email_smtp import send_email
                    
                    email_subject = action_config.get("subject") or trigger_config.get("email_subject") or f"{node.label or 'Sans titre'}"
                    logger.info(
                        "📧 [Executor] Envoi email: to=%s, subject=%s, body_text=%d chars, body_html=%d chars",
                        email_to,
                        email_subject,
                        len(body_text),
                        len(body_html),
                    )
                    
                    email_sent = send_email(
                        to_email=email_to,
                        subject=email_subject,
                        body_text=body_text,
                        body_html=body_html,
                    )
                    
                    if email_sent:
                        logger.info(f"✅ [Executor] Email envoyé à {email_to} pour l'action {action.name}")
                        output_result["email_sent"] = True
                        output_result["email_to"] = email_to
                    else:
                        logger.error(f"❌ [Executor] Échec de l'envoi d'email pour l'action {action.name}")
                        output_result["email_sent"] = False
                        status = ExecutionStatus.failed
                else:
                    logger.info(
                        "ℹ️ [Executor] Email non envoyé (output_type=%s, email_to=%s)",
                        output_type,
                        email_to,
                    )
                    output_result["email_sent"] = False
                    output_result["output_type"] = output_type
                    
            elif action_type == ActionType.send_email.value:
                # Action send_email (à implémenter si nécessaire)
                logger.warning(f"⚠️ [Executor] Action {action_type} non implémentée")
                output_result = {"message": "Action non implémentée"}
                
            else:
                # Autres types d'actions
                logger.info(f"ℹ️ [Executor] Action {action_type} exécutée (pas de logique spécifique)")
                output_result = {"executed_at": datetime.now(tz=timezone.utc).isoformat()}
                
        except Exception as e:
            logger.error(f"❌ [Executor] Erreur lors de l'exécution de l'action {action.name}: {e}", exc_info=True)
            status = ExecutionStatus.failed
            output_result = {"error": str(e)}
        
        # Logger l'exécution
        log = ExecutionLog(
            node_id=node_id,
            trigger_id=action.trigger_id,
            action_id=action.id,
            status=status,
            input_snapshot={"action": action_type, "config": action_config},
            output_snapshot=output_result,
        )
        session.add(log)
