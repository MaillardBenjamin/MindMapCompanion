import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone
from sqlalchemy import select, cast, String, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_AsyncSessionLocal
from app.models.enums import ActionType, EventType, MailProvider, NodeSource, NodeStatus, TriggerType
from app.models.mail_cache import MailCache
from app.models.node import Node
from app.models.mindmap import Trigger as MindmapTrigger
from app.services.agent_structurer import run_structurer_mindmap
from app.services.email_imap import fetch_unseen_messages, is_imap_configured
from app.services.executor import execute_actions_for_node
from app.services.events import get_or_create_event
from app.services.proposals import create_proposal

settings = get_settings()


def format_reminder_email(node: Node, action_config: dict) -> tuple[str, str]:
    """
    Formate un email de rappel d'échéance à partir d'un nœud et d'une configuration d'action.
    
    Args:
        node: Instance Node pour lequel formater l'email
        action_config: Configuration de l'action "reminder" (peut contenir un template personnalisé)
    
    Returns:
        Tuple (body_text, body_html) avec le contenu formaté de l'email
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Récupérer le template personnalisé si fourni, sinon utiliser le template par défaut
    template = action_config.get("template", "default")
    custom_template = action_config.get("custom_template")
    
    # Si un template personnalisé est fourni, l'utiliser
    if custom_template:
        # Remplacer les variables dans le template
        body_text = custom_template.get("text", "").format(
            title=node.title or "Sans titre",
            content=node.raw_text,
            due_date=node.due_date.strftime('%d/%m/%Y %H:%M') if node.due_date else "Non définie",
            tags=", ".join(node.tags) if node.tags else "Aucun",
            status=str(node.status) if node.status else "Non défini"
        )
        body_html = custom_template.get("html", "").format(
            title=node.title or "Sans titre",
            content=node.raw_text,
            due_date=node.due_date.strftime('%d/%m/%Y %H:%M') if node.due_date else "Non définie",
            tags=", ".join(node.tags) if node.tags else "Aucun",
            status=str(node.status) if node.status else "Non défini"
        )
        return body_text, body_html
    
    # Template par défaut
    body_text = f"Rappel d'échéance\n\n"
    body_text += f"Titre: {node.title or 'Sans titre'}\n"
    body_text += f"Contenu: {node.raw_text}\n"
    if node.due_date:
        body_text += f"Date d'échéance: {node.due_date.strftime('%d/%m/%Y %H:%M')}\n"
    if node.tags:
        body_text += f"Tags: {', '.join(node.tags)}\n"
    if node.status:
        body_text += f"Statut: {node.status}\n"
    
    # Construire le HTML de manière sécurisée
    html_parts = [
        "<html>",
        "<body style='font-family: Arial, sans-serif; line-height: 1.6; color: #333;'>",
        "<h2 style='color: #00D9FF;'>Rappel d'échéance</h2>",
        "<div style='background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;'>",
        f"<p><strong>Titre:</strong> {node.title or 'Sans titre'}</p>",
        f"<p><strong>Contenu:</strong> {node.raw_text}</p>",
    ]
    if node.due_date:
        html_parts.append(f"<p><strong>Date d'échéance:</strong> {node.due_date.strftime('%d/%m/%Y %H:%M')}</p>")
    if node.tags:
        html_parts.append(f"<p><strong>Tags:</strong> {', '.join(node.tags)}</p>")
    if node.status:
        html_parts.append(f"<p><strong>Statut:</strong> {node.status}</p>")
    html_parts.extend([
        "</div>",
        "</body>",
        "</html>"
    ])
    body_html = "\n".join(html_parts)
    
    return body_text, body_html


async def _process_email_batch(session: AsyncSession, messages: list[dict]) -> None:
    for message in messages:
        existing = await session.execute(
            select(MailCache).where(
                MailCache.idempotency_key == message["idempotency_key"]
            )
        )
        if existing.scalar_one_or_none():
            continue
        mail = MailCache(
            provider=MailProvider.imap,
            provider_message_id=message["provider_message_id"],
            from_addr=message["from_addr"],
            subject=message["subject"],
            snippet=message["snippet"],
            received_at=message["received_at"],
            raw_payload=message["raw_payload"],
            processed=False,
            idempotency_key=message["idempotency_key"],
        )
        session.add(mail)

        node = Node(
            raw_text=message["snippet"] or message["subject"],
            status=NodeStatus.inbox,
            source=NodeSource.email,
            source_ref={"provider_message_id": message["provider_message_id"]},
            tags=[],
            position={"x": 0, "y": 0},
        )
        session.add(node)
        await session.flush()

        await get_or_create_event(
            session,
            EventType.email_received,
            message["idempotency_key"],
            {"node_id": str(node.id)},
        )

        context = []
        proposal_json = run_structurer_mindmap(node.raw_text, context)
        await create_proposal(session, str(node.id), "StructurerMindmap", proposal_json)
        mail.processed = True


async def poll_imap() -> None:
    import logging
    log = logging.getLogger(__name__)
    try:
        # NOTE: `imaplib` est bloquant -> on l'exécute dans un thread pour ne pas bloquer l'event loop asyncio.
        messages = await asyncio.to_thread(fetch_unseen_messages)
        if not messages:
            return
        AsyncSessionLocal = get_AsyncSessionLocal()
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await _process_email_batch(session, messages)
    except Exception as e:
        log.warning("Poll IMAP failed: %s", e, exc_info=False)


async def execute_trigger_with_config(trigger: MindmapTrigger) -> None:
    """
    Exécute un trigger en utilisant sa configuration (agent ou action).
    
    Lit la configuration du trigger pour déterminer :
    - Le type de tâche (agent ou action)
    - L'ID de la tâche à exécuter
    - Le type de rendu (screen ou email)
    - Le texte d'entrée (pour les agents)
    
    Si output_type est "email", envoie le résultat par SMTP.
    Sinon, log simplement l'exécution.
    
    Args:
        trigger: Instance Trigger à exécuter.
    
    Note:
        Cette fonction est appelée par APScheduler pour les triggers cron
        et date_reached. Elle utilise une session DB synchrone pour
        compatibilité avec les CRUD existants.
    """
    import logging
    from app.services.configurable_agent_service import configurable_agent_service
    from app.crud import mindmap as crud_mindmap
    from app.database import SessionLocal
    
    logger = logging.getLogger(__name__)
    logger.info(f"🔄 [Scheduler] Exécution du trigger {trigger.id} (type: {trigger.trigger_type})")
    
    # `config` est stocké en JSON(B) et peut être NULL selon l'historique des données/migrations.
    # On normalise toujours en dict pour éviter les AttributeError (ex: config.get(...)).
    config = trigger.config or {}
    task_type = config.get("task_type", "action")
    task_id = config.get("selected_agent") or config.get("selected_action") or config.get("task_id")
    output_type = config.get("output_type", "screen")
    input_text = config.get("input_text")
    
    # Si pas de task_id mais output_type est "email", on peut envoyer un email direct (pour les échéances)
    # Vérifier d'abord s'il y a une action "reminder" à exécuter
    if not task_id and output_type == "email" and config.get("email_to"):
        AsyncSessionLocal = get_AsyncSessionLocal()
        async with AsyncSessionLocal() as async_session:
            async with async_session.begin():
                node = await async_session.get(Node, trigger.node_id)
                if not node:
                    logger.error(f"❌ [Scheduler] Nœud {trigger.node_id} introuvable pour le trigger {trigger.id}")
                    return
                
                # Chercher une action "reminder" pour ce nœud
                from app.models.action import Action
                from sqlalchemy import select
                
                reminder_action_result = await async_session.execute(
                    select(Action).where(
                        Action.node_id == trigger.node_id,
                        Action.action_type == ActionType.reminder,
                        Action.enabled.is_(True)
                    )
                )
                reminder_action = reminder_action_result.scalar_one_or_none()
                
                from app.services.email_smtp import send_email
                
                to_email = config.get("email_to")
                email_subject = config.get("email_subject") or f"Échéance: {node.title or node.raw_text[:50]}"
                
                # Si une action reminder existe, utiliser sa config pour formater le mail
                if reminder_action:
                    body_text, body_html = format_reminder_email(node, reminder_action.config)
                else:
                    # Format par défaut
                    body_text, body_html = format_reminder_email(node, {})
                
                email_sent = send_email(
                    to_email=to_email,
                    subject=email_subject,
                    body_text=body_text,
                    body_html=body_html,
                )
                
                if email_sent:
                    logger.info(f"✅ [Scheduler] Email d'échéance envoyé à {to_email} pour le trigger {trigger.id}")
                else:
                    logger.error(f"❌ [Scheduler] Échec de l'envoi d'email d'échéance pour le trigger {trigger.id}")
                
                # Mettre à jour last_fired_at
                trigger_db = await async_session.get(MindmapTrigger, trigger.id)
                if trigger_db:
                    trigger_db.last_fired_at = datetime.now(tz=timezone.utc).isoformat()
                
                return
    
    if not task_id:
        logger.warning(f"⚠️ [Scheduler] Trigger {trigger.id} n'a pas de task_id configuré")
        return
    
    # IMPORTANT: une partie du codebase (CRUD historique Mindmap/Trigger/Action) utilise encore une
    # session SQLAlchemy *synchrone*. On crée donc une session sync ici, tout en restant dans une
    # coroutine appelée par APScheduler (async). On évite de "mélanger" les objets ORM entre sessions.
    db_sync = SessionLocal()
    
    try:
        if task_type == "agent":
            # Exécuter un agent configurable
            from app.crud.configurable_agent import get_agent_by_id
            
            # Pour les triggers automatiques, il faut un `user_id` pour :
            # - autoriser l'accès à l'agent configurable (multi-tenant)
            # - attribuer correctement les logs d'exécution
            #
            # Aujourd'hui, les triggers cron/date sont exécutés "en background" sans contexte utilisateur
            # explicite. On lit le nœud associé pour récupérer un owner si possible (à améliorer).
            # FIXME: remplacer le fallback `user_id=1` par :
            # - owner du nœud (recommandé), ou
            # - un "user système" dédié (service account), ou
            # - stocker `user_id` directement sur Trigger.
            node = crud_mindmap.get_node(
                db_sync,
                trigger.node_id,
                None,  # pas de vérification user pour les triggers automatiques (à cadrer)
            )
            user_id = 1
            
            agent = get_agent_by_id(db_sync, int(task_id), user_id)
            if not agent:
                logger.error(f"❌ [Scheduler] Agent {task_id} introuvable pour le trigger {trigger.id}")
                return
            
            # Préparer le texte d'entrée
            if not input_text and node:
                input_text = node.description or node.label or ""
            
            # Récupérer les options de l'agent depuis la config du trigger
            agent_options = config.get("agent_options", {})
            
            logger.info(f"🤖 [Scheduler] Exécution de l'agent {agent.name} (ID: {agent.id})")
            logger.info(f"🤖 [Scheduler] Options de l'agent: {agent_options}")
            
            # Exécuter l'agent avec les options
            result = await configurable_agent_service.execute_agent(
                db=db_sync,
                agent_id=agent.id,
                user_id=user_id,
                input_text=input_text or "",
                options=agent_options,
            )
            
            # Gérer le rendu de sortie
            if output_type == "email" and config.get("email_to"):
                from app.services.email_smtp import send_email, format_agent_output_as_email
                
                to_email = config.get("email_to")
                email_subject = config.get("email_subject") or f"Résultat de l'agent {agent.name}"
                
                body_text, body_html = format_agent_output_as_email(
                    output_raw=result.get("output_raw", ""),
                    output_parsed=result.get("output_parsed"),
                    agent_name=agent.name,
                    input_text=input_text,
                    execution_time_ms=result.get("execution_time_ms"),
                )
                
                email_sent = send_email(
                    to_email=to_email,
                    subject=email_subject,
                    body_text=body_text,
                    body_html=body_html,
                )
                
                if email_sent:
                    logger.info(f"✅ [Scheduler] Email envoyé à {to_email} pour le trigger {trigger.id}")
                else:
                    logger.error(f"❌ [Scheduler] Échec de l'envoi d'email pour le trigger {trigger.id}")
            
            logger.info(f"✅ [Scheduler] Agent exécuté avec succès pour le trigger {trigger.id}")
            
        elif task_type == "action":
            # Exécuter les actions du nœud
            AsyncSessionLocal = get_AsyncSessionLocal()
            async with AsyncSessionLocal() as async_session:
                async with async_session.begin():
                    await execute_actions_for_node(
                        session=async_session,
                        node_id=trigger.node_id,
                        trigger_id=trigger.id,
                    )
            logger.info(f"✅ [Scheduler] Actions exécutées pour le trigger {trigger.id}")
        
        # Mettre à jour last_fired_at : on le fait en async (session async dédiée) pour éviter
        # de conserver trop longtemps la session sync et pour standardiser les écritures côté scheduler.
        AsyncSessionLocal = get_AsyncSessionLocal()
        async with AsyncSessionLocal() as async_session:
            async with async_session.begin():
                trigger_db = await async_session.get(MindmapTrigger, trigger.id)
                if trigger_db:
                    trigger_db.last_fired_at = datetime.now(tz=timezone.utc).isoformat()
                    await async_session.commit()
        
    except Exception as e:
        logger.error(f"❌ [Scheduler] Erreur lors de l'exécution du trigger {trigger.id}: {e}", exc_info=True)
    finally:
        db_sync.close()


async def run_due_triggers() -> None:
    """
    Exécute les triggers date_reached qui sont dus.
    Note: Les triggers cron sont gérés directement par APScheduler.
    """
    now = datetime.now(tz=timezone.utc)
    AsyncSessionLocal = get_AsyncSessionLocal()
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Convertir l'enum PostgreSQL en texte pour la comparaison
            # La colonne trigger_type est un enum dans la DB mais String dans le modèle
            result = await session.execute(
                select(MindmapTrigger).where(
                    MindmapTrigger.enabled.is_(True),
                    text("triggers.trigger_type::text = :trigger_type_val")
                ).params(trigger_type_val=TriggerType.date_reached.value)
            )
            for trigger in result.scalars().all():
                run_at = trigger.config.get("run_at")
                if not run_at or trigger.last_fired_at:
                    continue
                try:
                    run_at_dt = datetime.fromisoformat(run_at)
                except ValueError:
                    continue
                if run_at_dt <= now:
                    trigger.last_fired_at = now.isoformat()
                    await execute_trigger_with_config(trigger)


def parse_cron_expression(cron_expr: str) -> dict:
    """
    Parse une expression cron en paramètres pour APScheduler.
    
    Format attendu: "minute heure * * jours"
    - minute: 0-59 ou *
    - heure: 0-23 ou *
    - jours: 0-6 (0=dimanche) ou * ou liste comme "1,3,5"
    
    Args:
        cron_expr: Expression cron au format "minute heure * * jours".
    
    Returns:
        Dict avec les clés 'minute', 'hour', 'day_of_week' si spécifiés.
        Exemple: {"minute": "0", "hour": "9", "day_of_week": "1,3,5"}
    
    Raises:
        ValueError: Si l'expression cron est invalide (pas 5 parties).
    
    Example:
        >>> params = parse_cron_expression("0 9 * * 1,3,5")
        >>> print(params)
        {"minute": "0", "hour": "9", "day_of_week": "1,3,5"}
    """
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Expression cron invalide: {cron_expr}")
    
    minute = parts[0]
    hour = parts[1]
    day_of_month = parts[2]  # Ignoré pour l'instant
    month = parts[3]  # Ignoré pour l'instant
    day_of_week = parts[4]
    
    params = {}
    
    # Minute
    if minute != "*":
        params["minute"] = minute
    
    # Heure
    if hour != "*":
        params["hour"] = hour
    
    # Jour de la semaine (0=dimanche, 6=samedi dans cron standard)
    if day_of_week != "*":
        # APScheduler utilise aussi 0=dimanche, 6=samedi
        params["day_of_week"] = day_of_week
    
    return params


async def load_cron_triggers(scheduler: AsyncIOScheduler) -> None:
    """
    Charge les triggers cron depuis la DB et les ajoute au scheduler.
    
    Récupère tous les triggers de type "cron" activés, parse leur expression
    cron, et les ajoute comme jobs APScheduler. Supprime d'abord les jobs
    existants pour éviter les doublons.
    
    Args:
        scheduler: Instance AsyncIOScheduler où ajouter les jobs.
    
    Note:
        Les triggers sans expression cron valide sont ignorés avec un warning.
        Les erreurs lors de l'ajout sont loggées mais n'interrompent pas le processus.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    AsyncSessionLocal = get_AsyncSessionLocal()
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Convertir l'enum PostgreSQL en texte pour la comparaison
            # La colonne trigger_type est un enum dans la DB mais String dans le modèle
            result = await session.execute(
                select(MindmapTrigger).where(
                    MindmapTrigger.enabled.is_(True),
                    text("triggers.trigger_type::text = :trigger_type_val")
                ).params(trigger_type_val=TriggerType.cron.value)
            )
            triggers = result.scalars().all()
            
            for trigger in triggers:
                # Gérer le cas où config est None
                config = trigger.config or {}
                cron_expression = config.get("cron_expression")
                if not cron_expression:
                    logger.warning(f"⚠️ [Scheduler] Trigger cron {trigger.id} n'a pas d'expression cron (config: {config})")
                    continue
                
                # Supprimer le job existant s'il existe
                job_id = f"cron_trigger_{trigger.id}"
                try:
                    scheduler.remove_job(job_id)
                except:
                    pass
                
                # Ajouter le job cron
                try:
                    # APScheduler peut utiliser directement l'expression cron en string
                    # ou on peut parser pour plus de contrôle
                    cron_params = parse_cron_expression(cron_expression)
                    
                    scheduler.add_job(
                        execute_trigger_with_config,
                        trigger="cron",
                        id=job_id,
                        replace_existing=True,
                        args=[trigger],
                        **cron_params
                    )
                    logger.info(f"✅ [Scheduler] Trigger cron {trigger.id} ajouté: {cron_expression}")
                except Exception as e:
                    logger.error(f"❌ [Scheduler] Erreur lors de l'ajout du trigger cron {trigger.id}: {e}", exc_info=True)


def start_scheduler() -> AsyncIOScheduler:
    """
    Démarre le scheduler avec les jobs configurés.
    
    Configure et démarre APScheduler avec :
    - Poll IMAP : Récupération des emails toutes les N minutes (config.imap_poll_minutes)
    - Run due triggers : Vérification des triggers date_reached toutes les minutes
    - Load cron triggers : Chargement initial des triggers cron depuis la DB
    - Reload cron triggers : Rechargement périodique (toutes les 5 min) pour détecter les changements
    - Job offers cleanup : Nettoyage hebdomadaire des offres d'emploi expirées
    
    Returns:
        AsyncIOScheduler: Instance du scheduler démarré.
    
    Note:
        Le scheduler doit être arrêté proprement lors de l'arrêt de l'application
        via app.on_event("shutdown").
    """
    import logging
    import asyncio
    logger = logging.getLogger(__name__)
    
    # Configurer le scheduler avec UTC pour cohérence avec date_reached
    scheduler = AsyncIOScheduler(timezone="UTC")
    
    # Job pour poller les emails IMAP (uniquement si IMAP configuré dans .env)
    if is_imap_configured():
        scheduler.add_job(poll_imap, "interval", minutes=settings.imap_poll_minutes, id="poll_imap")
        logger.info("✅ [Scheduler] Poll IMAP activé (toutes les %d min)", settings.imap_poll_minutes)
    else:
        logger.info("⏭️ [Scheduler] Poll IMAP désactivé (IMAP_HOST, IMAP_USER, IMAP_PASSWORD non configurés)")
    
    # Job pour vérifier les triggers date_reached
    scheduler.add_job(run_due_triggers, "interval", minutes=1, id="run_due_triggers")
    
    # Charger les triggers cron au démarrage
    async def load_cron_on_startup():
        await load_cron_triggers(scheduler)
    
    # Exécuter le chargement des triggers cron au démarrage
    asyncio.create_task(load_cron_on_startup())
    
    # Recharger les triggers cron toutes les 5 minutes (au cas où ils sont modifiés)
    async def reload_cron_triggers():
        await load_cron_triggers(scheduler)
    
    scheduler.add_job(reload_cron_triggers, "interval", minutes=5, id="reload_cron_triggers")
    
    # Job pour nettoyer les offres d'emploi expirées (hebdomadaire, dimanche 2h)
    try:
        from app.services.job_scraping.cleanup_scheduler import run_scheduled_cleanup
        
        scheduler.add_job(
            run_scheduled_cleanup,
            trigger="cron",
            id="job_offers_cleanup",
            day_of_week="sun",  # Dimanche
            hour=2,             # 2h du matin
            minute=0,
            replace_existing=True,
        )
        logger.info("✅ [Scheduler] Job de nettoyage des offres d'emploi configuré (dimanche 2h)")
    except ImportError as e:
        logger.warning(f"⚠️ [Scheduler] Module de nettoyage des offres non disponible: {e}")
    except Exception as e:
        logger.error(f"❌ [Scheduler] Erreur configuration nettoyage offres: {e}", exc_info=True)
    
    scheduler.start()
    logger.info("🚀 [Scheduler] Scheduler démarré")
    return scheduler
