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


async def _write_agent_results_to_graph(
    trigger: MindmapTrigger,
    result: dict,
    db_sync,
) -> None:
    """
    Écrit les résultats d'un agent dans le graphe sous forme de nœuds enfants
    rattachés au nœud du trigger.

    Gère deux formats de sortie :
    - JSON structuré avec ``key_findings`` : un nœud par finding
    - Markdown brut : un nœud résumé unique
    """
    from app.models.mindmap import Node as MindmapNode
    from app.crud.mindmap import create_node as crud_create_node
    from app.schemas.mindmap import NodeCreate

    logger_wg = logging.getLogger(__name__)

    parent_node = (
        db_sync.query(MindmapNode)
        .filter(MindmapNode.id == trigger.node_id)
        .first()
    )
    if not parent_node:
        logger_wg.error(
            "❌ [WriteToGraph] Nœud %d introuvable", trigger.node_id
        )
        return

    output_parsed = result.get("output_parsed")
    output_raw = result.get("output_raw", "")
    agent_name = result.get("agent_name", "Agent")

    if not output_parsed and not output_raw:
        return

    mindmap_id = parent_node.mindmap_id
    parent_id = parent_node.id

    existing_children = (
        db_sync.query(MindmapNode)
        .filter(
            MindmapNode.parent_id == parent_id,
            MindmapNode.mindmap_id == mindmap_id,
        )
        .count()
    )

    nodes_created = []

    if isinstance(output_parsed, dict) and isinstance(
        output_parsed.get("key_findings"), list
    ):
        from datetime import datetime as _dt

        date_label = _dt.now().strftime("%d/%m/%Y")
        report_node = NodeCreate(
            mindmap_id=mindmap_id,
            parent_id=parent_id,
            label=f"Rapport {date_label}"[:50],
            description=output_parsed.get("executive_summary", ""),
            position_x=parent_node.position_x + 200,
            position_y=parent_node.position_y + (existing_children * 80),
            status="inbox",
        )
        try:
            report = crud_create_node(db_sync, report_node)
            nodes_created.append(report.id)
        except Exception as e:
            logger_wg.error("❌ [WriteToGraph] Erreur création nœud rapport : %s", e)
            return

        for i, finding in enumerate(output_parsed["key_findings"]):
            if not isinstance(finding, dict):
                continue
            label = (finding.get("title") or f"Point {i + 1}")[:50]
            parts = [finding.get("description", "")]
            if finding.get("source"):
                parts.append(f"Source : {finding['source']}")
            if finding.get("importance"):
                parts.append(f"Importance : {finding['importance']}")
            description = "\n".join(p for p in parts if p)

            node_create = NodeCreate(
                mindmap_id=mindmap_id,
                parent_id=report.id,
                label=label,
                description=description,
                position_x=report.position_x + 200,
                position_y=report.position_y + (i * 80),
                status="inbox",
            )
            try:
                new_node = crud_create_node(db_sync, node_create)
                nodes_created.append(new_node.id)
            except Exception as e:
                logger_wg.error(
                    "❌ [WriteToGraph] Erreur création nœud finding : %s", e
                )
    else:
        from datetime import datetime as _dt

        date_label = _dt.now().strftime("%d/%m/%Y")
        summary = ""
        if isinstance(output_parsed, dict):
            summary = output_parsed.get("executive_summary", "")
        if not summary:
            summary = output_raw[:200]
        label = f"Rapport {agent_name} – {date_label}"[:50]

        node_create = NodeCreate(
            mindmap_id=mindmap_id,
            parent_id=parent_id,
            label=label,
            description=output_raw[:4000],
            position_x=parent_node.position_x + 200,
            position_y=parent_node.position_y + (existing_children * 80),
            status="inbox",
        )
        try:
            new_node = crud_create_node(db_sync, node_create)
            nodes_created.append(new_node.id)
        except Exception as e:
            logger_wg.error(
                "❌ [WriteToGraph] Erreur création nœud résumé : %s", e
            )

    if nodes_created:
        logger_wg.info(
            "✅ [WriteToGraph] %d nœud(s) créé(s) sous le nœud %d : %s",
            len(nodes_created),
            parent_id,
            nodes_created,
        )


async def execute_trigger_with_config(trigger: MindmapTrigger | int) -> None:
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
        trigger: Instance Trigger OU **id entier** (jobs APScheduler : préférer l'id pour
            éviter les instances ORM détachées/expirées).
    
    Note:
        Cette fonction est appelée par APScheduler pour les triggers cron
        et date_reached. Elle utilise une session DB synchrone pour
        compatibilité avec les CRUD existants.
    """
    import logging
    from types import SimpleNamespace

    from app.services.configurable_agent_service import configurable_agent_service
    from app.crud import mindmap as crud_mindmap
    from app.database import SessionLocal
    
    logger = logging.getLogger(__name__)
    tid = trigger if isinstance(trigger, int) else trigger.id
    # Recharger depuis la DB (session synchrone) : les jobs cron ne doivent pas
    # réutiliser un ORM détaché après fermeture de la session de load_cron_triggers.
    _db_reload = SessionLocal()
    try:
        row = _db_reload.query(MindmapTrigger).filter(MindmapTrigger.id == tid).first()
    finally:
        _db_reload.close()
    if not row:
        logger.error("❌ [Scheduler] Trigger %s introuvable en base", tid)
        return
    cfg_raw = row.config
    if cfg_raw is None:
        cfg = {}
    elif isinstance(cfg_raw, dict):
        cfg = dict(cfg_raw)
    else:
        cfg = {}
    tt = getattr(row.trigger_type, "value", row.trigger_type)
    trigger = SimpleNamespace(
        id=row.id,
        node_id=row.node_id,
        trigger_type=tt,
        config=cfg,
    )
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

            if output_type == "mindmap_child" and result:
                from app.crud.mindmap import get_node_by_id
                from app.services.agent_result_child_node import create_child_from_agent_output

                parent_node = get_node_by_id(db_sync, trigger.node_id)
                if parent_node:
                    try:
                        normalized = {
                            "output_raw": result.get("output_raw"),
                            "output_parsed": result.get("output_parsed"),
                        }
                        child = create_child_from_agent_output(db_sync, parent_node, normalized)
                        logger.info(
                            "✅ [Scheduler] Nœud enfant mindmap_child créé: id=%s label=%s",
                            child.id,
                            child.label,
                        )
                    except ValueError as e:
                        logger.error(
                            "❌ [Scheduler] Échec création nœud mindmap_child: %s",
                            e,
                        )
                else:
                    logger.error(
                        "❌ [Scheduler] Nœud parent %s introuvable pour mindmap_child",
                        trigger.node_id,
                    )
            
            # Écrire les résultats dans le graphe si configuré
            if config.get("write_to_graph") and result:
                try:
                    await _write_agent_results_to_graph(
                        trigger=trigger,
                        result=result,
                        db_sync=db_sync,
                    )
                except Exception as e:
                    logger.error(
                        "❌ [Scheduler] Erreur write_to_graph pour le trigger %d : %s",
                        trigger.id, e, exc_info=True,
                    )

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

        # Notifier les clients web (polling sync-revision) que le graphe peut avoir changé
        try:
            from app.services.mindmap_revision import bump_mindmap_revision

            n = crud_mindmap.get_node_by_id(db_sync, trigger.node_id)
            if n:
                bump_mindmap_revision(n.mindmap_id)
        except Exception as bump_err:
            logger.warning("Révision mindmap non mise à jour: %s", bump_err)

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


def cron_expression_from_trigger_config(config: dict) -> str | None:
    """
    Expression cron pour APScheduler : priorité à `cron_expression` en base,
    sinon reconstruction depuis cron_hour / cron_minute / cron_days (logique alignée sur le frontend).
    """
    raw = config.get("cron_expression")
    if raw is not None and str(raw).strip():
        return str(raw).strip()

    hour = config.get("cron_hour")
    minute = config.get("cron_minute")
    days = config.get("cron_days")
    if hour is None and minute is None and not days:
        return None

    local_h = int(hour) if hour is not None else 9
    local_m = int(minute) if minute is not None else 0
    day_list: list[int] = []
    if isinstance(days, list):
        for x in days:
            try:
                day_list.append(int(x))
            except (TypeError, ValueError):
                continue

    now = datetime.now().astimezone()
    local_dt = now.replace(hour=local_h, minute=local_m, second=0, microsecond=0)
    utc_dt = local_dt.astimezone(timezone.utc)
    utc_h = utc_dt.hour
    utc_m = utc_dt.minute

    if not day_list or len(day_list) == 7:
        return f"{utc_m} {utc_h} * * *"
    days_str = ",".join(str(d) for d in sorted(set(day_list)))
    return f"{utc_m} {utc_h} * * {days_str}"


async def load_cron_triggers(scheduler: AsyncIOScheduler) -> None:
    """
    Charge les triggers cron depuis la DB et les ajoute au scheduler.
    
    Utilise la **session SQLAlchemy synchrone** (comme le CRUD mindmap) pour éviter
    une dépendance silencieuse à asyncpg / une tâche asyncio qui échoue sans log.
    
    Les jobs passent uniquement l'**id** du trigger à execute_trigger_with_config
    (instance ORM rechargée au moment de l'exécution).
    """
    import logging
    from app.database import SessionLocal as SyncSessionLocal

    logger = logging.getLogger(__name__)
    db = SyncSessionLocal()
    rows: list = []
    try:
        rows = (
            db.query(MindmapTrigger)
            .filter(MindmapTrigger.enabled.is_(True))
            .filter(text("triggers.trigger_type::text = :trigger_type_val"))
            .params(trigger_type_val=TriggerType.cron.value)
            .all()
        )
    except Exception as e:
        logger.error(
            "❌ [Scheduler] Impossible de lister les triggers cron (session sync): %s",
            e,
            exc_info=True,
        )
        return
    finally:
        db.close()

    logger.info("📅 [Scheduler] %d trigger(s) cron actif(s) trouvé(s) en base", len(rows))

    for trigger_row in rows:
        config = trigger_row.config or {}
        if not isinstance(config, dict):
            config = {}
        cron_expression = config.get("cron_expression")
        if not cron_expression:
            cron_expression = cron_expression_from_trigger_config(config)
        tid = trigger_row.id
        if not cron_expression:
            logger.warning(
                "⚠️ [Scheduler] Trigger cron %s n'a pas d'expression cron "
                "(config vide ou incomplète : %s)",
                tid,
                config,
            )
            continue

        job_id = f"cron_trigger_{tid}"
        try:
            scheduler.remove_job(job_id)
        except Exception:
            pass

        try:
            cron_params = parse_cron_expression(cron_expression)
            scheduler.add_job(
                execute_trigger_with_config,
                trigger="cron",
                id=job_id,
                replace_existing=True,
                args=[tid],
                misfire_grace_time=300,
                **cron_params,
            )
            logger.info("✅ [Scheduler] Trigger cron %s ajouté: %s", tid, cron_expression)
        except Exception as e:
            logger.error(
                "❌ [Scheduler] Erreur lors de l'ajout du trigger cron %s: %s",
                tid,
                e,
                exc_info=True,
            )


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
    
    # Chargement initial des triggers cron : fait dans main.py (startup) via await load_cron_triggers(...)
    
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
