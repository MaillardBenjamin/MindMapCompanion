"""
Configuration automatique des triggers après génération de nœuds (Assistant IA).

Sélection d'un agent configurable via un appel LLM court, puis création de triggers
sur chaque feuille du lot ``created_nodes``. Type de rendu par défaut : ``mindmap_child`` ;
détection heuristique du texte pour ``screen``, ``email``, ``audio_tts``, ``audio_email``.
Si le texte utilisateur décrit une récurrence (ex. « tous les lundi à 7h »), les feuilles
dont le libellé/description évoquent une exécution planifiée reçoivent un trigger ``cron``
avec heure et jours initialisés.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.agno_model import get_agno_chat_model, is_ollama_configured
from app.core.config import get_settings
from app.crud.configurable_agent import get_agents as get_configurable_agents
from app.crud.configurable_agent import get_agent_by_id
from app.crud.mindmap import create_trigger
from app.schemas.mindmap import TriggerCreate
from app.services.scheduler import cron_expression_from_trigger_config

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# Feuille « agent / veille / horaire » : reçoit le cron si plusieurs feuilles et planification détectée
_CRON_LEAF_HINT = re.compile(
    r"(veille|automatis|planif(i|ie)|agent\s+de|exécution|execution|hebdomadaire|"
    r"quotidien|journalier|\bcron\b|\d{1,2}\s*:\s*\d{2}|"
    r"\b(lun|mar|mer|jeu|ven|sam|dim)\b.{0,40}\d)",
    re.IGNORECASE,
)

_LLM_INSTRUCTIONS = """Tu es un routeur d'agents pour un mindmap.
On te donne un CONTEXTE (texte utilisateur + nœud) et une liste d'AGENTS avec leurs id numériques.
Choisis au plus UN agent dont le rôle et la description correspondent au mieux au contexte pour traiter ce nœud.
Réponds UNIQUEMENT avec un JSON valide, sans texte avant ni après, au format exact:
{"agent_id": <nombre entier parmi les id proposés, ou null>, "reasoning": "<une courte phrase>"}
Si aucun agent n'est vraiment adapté, mets agent_id à null."""


def _extract_json_object(text: str) -> Optional[str]:
    if not text:
        return None
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for i, ch in enumerate(text[start:], start=start):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _parse_llm_json(content: str) -> Dict[str, Any]:
    cleaned = (content or "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    extracted = _extract_json_object(cleaned)
    if extracted:
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            pass
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    raise ValueError(f"JSON non parsable: {content[:200]}...")


def _run_agent_choice_llm(user_prompt: str) -> Dict[str, Any]:
    """Appelle le LLM (Agno) pour obtenir agent_id + reasoning. À mocker dans les tests."""
    settings = get_settings()
    if not is_ollama_configured() and not settings.agno_api_key and not settings.openai_api_key:
        raise RuntimeError(
            "Aucune config LLM (OLLAMA_BASE_URL ou AGNO_API_KEY / OPENAI_API_KEY)."
        )

    from agno.agent import Agent

    model = get_agno_chat_model()
    agent = Agent(
        model=model,
        instructions=[_LLM_INSTRUCTIONS],
    )
    result = agent.run(f"{_LLM_INSTRUCTIONS}\n\n{user_prompt}")
    raw = getattr(result, "content", None) or getattr(result, "output", None) or result
    return _parse_llm_json(str(raw))


def parse_recurring_schedule_french(text: str) -> Optional[Dict[str, Any]]:
    """
    Détecte jour(s) de la semaine et heure locale dans un texte (français courant).

    Retourne ``cron_days`` (0=dimanche … 6=samedi, aligné UI), ``cron_hour``, ``cron_minute``.
    Retourne ``None`` si aucune planification récurrente n'est identifiable.
    """
    if not text or not str(text).strip():
        return None
    t = str(text).lower().replace("’", "'")

    day_nums: set[int] = set()
    day_patterns = [
        (r"\bdimanches?\b", 0),
        (r"\blundis?\b", 1),
        (r"\bmardis?\b", 2),
        (r"\bmercredis?\b", 3),
        (r"\bjeudis?\b", 4),
        (r"\bvendredis?\b", 5),
        (r"\bsamedis?\b", 6),
    ]
    for pat, num in day_patterns:
        if re.search(pat, t):
            day_nums.add(num)

    if re.search(r"\bjours?\s+ouvrables?\b|\blundi\s+au\s+vendredi\b", t):
        day_nums.update({1, 2, 3, 4, 5})
    if re.search(r"\bweek[- ]?end\b|\bweekends?\b", t):
        day_nums.update({0, 6})

    daily = bool(
        re.search(
            r"\btous les jours\b|\bchaque jour\b|\bquotidien\b|\bjournalier\b|"
            r"\bchaque matin\b|\bchaque soir\b",
            t,
        )
    )

    hour: Optional[int] = None
    minute = 0

    m = re.search(r"\b(?:à|a)\s*(\d{1,2})\s*h(?:([0-5]?\d))?\b", t)
    if m:
        hour = int(m.group(1))
        if m.group(2):
            minute = int(m.group(2))
    if hour is None:
        m = re.search(r"\b(\d{1,2}):(\d{2})\b", t)
        if m:
            hour, minute = int(m.group(1)), int(m.group(2))
    if hour is None:
        m = re.search(r"\b(\d{1,2})\s*h\b", t)
        if m:
            hour = int(m.group(1))

    has_day = bool(day_nums) or daily
    has_time = hour is not None

    if not has_day and not has_time:
        return None

    if daily:
        cron_days = list(range(7))
    elif day_nums:
        cron_days = sorted(day_nums)
    else:
        # Heure sans jour explicite → tous les jours à cette heure
        cron_days = list(range(7))

    if hour is None:
        hour = 9
    if hour > 23 or minute > 59:
        return None

    return {"cron_days": cron_days, "cron_hour": hour, "cron_minute": minute}


def infer_output_delivery_from_text(user_text: str) -> Dict[str, Optional[str]]:
    """
    Déduit ``output_type`` et champs email depuis une phrase utilisateur (sans LLM).

    Valeurs possibles pour ``output_type`` :
    - ``audio_email`` : sortie parlée + livraison à une adresse extraite.
    - ``email`` : livraison texte par courriel + adresse + intention d'envoi / réception.
    - ``audio_tts`` : sortie parlée sans envoi par mail (synonyme du rendu « Audio (TTS) »).
    - ``screen`` : affichage dans l'interface (synonyme du rendu « À l'écran »).
    - ``mindmap_child`` : défaut lorsqu'aucun canal n'est identifiable clairement.

    Retourne ``output_type``, ``email_to``, ``email_subject`` (motif « sujet : ... »).
    """
    default: Dict[str, Optional[str]] = {
        "output_type": "mindmap_child",
        "email_to": None,
        "email_subject": None,
    }
    if not user_text or not str(user_text).strip():
        return default

    text = str(user_text)
    t_lower = text.lower().replace("’", "'")

    emails = _EMAIL_RE.findall(text)
    email_to = emails[0] if emails else None

    wants_spoken_output = bool(
        re.search(
            r"\baudio(s)?\b|\btts\b|text[-\s]?to[-\s]?speech|synthèse\s+vocale|"
            r"fichier\s+(audio|son|mp3)|\b(mp3|wav|mpeg)\b|"
            r"\b(écouter|entendre|à\s+l['']oral)\b",
            t_lower,
        )
    )

    wants_on_screen = bool(
        re.search(
            r"\b(à|sur)\s+l['']?(?:é|e)cran\b|"
            r"\baffich(?:er|age)?\s+(?:sur\s+)?l['']?(?:é|e)cran\b|"
            r"\bdans\s+l['']?(?:application|appli|interface)\b",
            t_lower,
        )
    )

    mail_delivery_intent = bool(
        re.search(
            r"\b(par|via|avec|en)\s+(courriel|mail|mél|emails?|e-mail)\b|"
            r"\bà\s+l['']adresse\b|"
            r"\benvoy",
            t_lower,
        )
    )

    recevoir_with_address = bool(re.search(r"\brecevoir\b", t_lower)) and bool(email_to)

    subj_m = re.search(
        r"\bsujet\s*(?:email|courriel)?\s*[:]\s*([^\n.]{1,200})",
        text,
        re.IGNORECASE,
    )
    email_subject = subj_m.group(1).strip() if subj_m else None

    # 1) Audio + adresse → audio par email
    if email_to and wants_spoken_output:
        return {
            "output_type": "audio_email",
            "email_to": email_to,
            "email_subject": email_subject,
        }

    # 2) Courriel texte + adresse
    if email_to and (mail_delivery_intent or recevoir_with_address) and not wants_spoken_output:
        return {
            "output_type": "email",
            "email_to": email_to,
            "email_subject": email_subject,
        }

    # 3) Audio sans livraison mail → TTS
    if wants_spoken_output:
        return {
            "output_type": "audio_tts",
            "email_to": None,
            "email_subject": email_subject,
        }

    # 4) Affichage interface, sans demande audio
    if wants_on_screen:
        return {
            "output_type": "screen",
            "email_to": None,
            "email_subject": email_subject,
        }

    return default


def leaf_matches_cron_context(label: str, description: str) -> bool:
    blob = f"{label or ''} {description or ''}".strip()
    if not blob:
        return False
    return bool(_CRON_LEAF_HINT.search(blob))


def _should_use_cron_for_leaf(
    schedule: Optional[Dict[str, Any]],
    leaf_ids: List[int],
    label: str,
    description: str,
) -> bool:
    if not schedule:
        return False
    if len(leaf_ids) == 1:
        return True
    return leaf_matches_cron_context(label, description)


def _score_leaf_against_user_text(user_text: str, label: str, description: str) -> int:
    """Mots significatifs du texte utilisateur présents dans titre + description (évite les doublons de nœuds)."""
    if not user_text:
        return 0
    words = re.findall(
        r"[a-zàâäéèêëïîôùûçA-ZÀÂÄÉÈÊËÏÎÔÙÛÇ]{4,}",
        user_text.lower(),
    )
    blob = f"{label} {description}".lower()
    return sum(1 for w in set(words) if w in blob)


def _looks_like_schedule_only_node(label: str, description: str) -> bool:
    """Nœud créé par erreur uniquement pour l'horaire, sans le fond métier."""
    blob = f"{label} {description}".lower()
    if len(blob) > 500:
        return False
    substance = (
        "climat",
        "bourse",
        "financ",
        "marché",
        "impact",
        "répercussion",
        "veille",
        "surveillance",
        "agent",
        "thème",
        "sujet",
    )
    has_substance = any(s in blob for s in substance)
    if has_substance:
        return False
    schedule_cues = (
        "hebdo",
        "lun ",
        "lundi",
        "07h",
        "07:00",
        "planification",
        "exécution tous",
        "chaque semaine",
    )
    has_sched = any(c in blob for c in schedule_cues)
    short_title = len((label or "").strip()) < 36
    return has_sched and short_title


def _filter_leaves_for_scheduled_single_job(
    leaf_ids: List[int],
    schedule: Optional[Dict[str, Any]],
    nodes_by_id: Dict[int, Dict[str, Any]],
    orm_by_id: Dict[int, Any],
    user_text: str,
) -> List[int]:
    """
    Si une planification est dans le texte mais que le modèle a créé plusieurs feuilles,
    un seul nœud doit porter le trigger (celui qui reflète le mieux l'intent utilisateur).
    """
    if not schedule or len(leaf_ids) <= 1:
        return leaf_ids

    scored: List[tuple[int, int]] = []
    for lid in leaf_ids:
        info = nodes_by_id.get(lid, {})
        label = info.get("label") or ""
        desc = ""
        o = orm_by_id.get(lid)
        if o is not None:
            desc = getattr(o, "description", None) or ""
        score = _score_leaf_against_user_text(user_text, label, desc)
        if _looks_like_schedule_only_node(label, desc):
            score -= 100
        scored.append((score, lid))

    scored.sort(key=lambda x: (-x[0], x[1]))
    best_id = scored[0][1]
    logger.info(
        "[AssistantTriggerSetup] Plusieurs feuilles + planification détectée: "
        "un seul trigger sur le nœud %s (scores: %s)",
        best_id,
        scored,
    )
    return [best_id]


def _build_trigger_config_base(
    agent_id: int,
    *,
    use_cron: bool,
    schedule: Optional[Dict[str, Any]],
    output_type: str = "mindmap_child",
    email_to: Optional[str] = None,
    email_subject: Optional[str] = None,
) -> Dict[str, Any]:
    ot = output_type if output_type in (
        "mindmap_child",
        "screen",
        "email",
        "audio_tts",
        "audio_email",
    ) else "mindmap_child"
    cfg: Dict[str, Any] = {
        "task_type": "agent",
        "selected_agent": str(agent_id),
        "output_type": ot,
    }
    if ot in ("email", "audio_email"):
        if email_to:
            cfg["email_to"] = email_to
        if email_subject:
            cfg["email_subject"] = email_subject
    if use_cron and schedule:
        cfg["cron_hour"] = schedule["cron_hour"]
        cfg["cron_minute"] = schedule["cron_minute"]
        cfg["cron_days"] = schedule["cron_days"]
        expr = cron_expression_from_trigger_config(cfg)
        if expr:
            cfg["cron_expression"] = expr
    return cfg


def find_leaf_node_ids(created_nodes: List[Dict[str, Any]]) -> List[int]:
    """
    Nœuds feuilles dans le lot : aucun autre élément de ``created_nodes`` n'a ce nœud comme parent.
    """
    if not created_nodes:
        return []
    parent_ids = {n.get("parent_id") for n in created_nodes if n.get("parent_id") is not None}
    all_ids = {n["id"] for n in created_nodes}
    leaf_ids = [n["id"] for n in created_nodes if n["id"] not in parent_ids]
    logger.info(
        "[AssistantTriggerSetup] lot: %d nœuds, %d feuilles: %s",
        len(all_ids),
        len(leaf_ids),
        leaf_ids,
    )
    return leaf_ids


def _build_agents_catalog(agents) -> str:
    rows = []
    for a in agents:
        tools = a.tools if isinstance(a.tools, list) else (a.tools or [])
        rows.append(
            {
                "id": a.id,
                "name": a.name,
                "description": (a.description or "")[:500],
                "persona": (a.persona or "")[:300],
                "instructions": (a.instructions or "")[:400],
                "tools": tools[:20] if tools else [],
            }
        )
    return json.dumps(rows, ensure_ascii=False, indent=2)


def select_best_agent(
    db: Session,
    user_id: int,
    context_text: str,
) -> Optional[Any]:
    """
    Retourne l'instance ``ConfigurableAgent`` choisie par le LLM, ou ``None``.
    """
    agents = get_configurable_agents(db, user_id=user_id, include_public=True)
    if not agents:
        logger.info("[AssistantTriggerSetup] Aucun agent configurable actif")
        return None

    valid_ids = {a.id for a in agents}
    catalog = _build_agents_catalog(agents)
    user_prompt = f"""CONTEXTE (tâche / nœud à traiter):
{context_text.strip()}

AGENTS DISPONIBLES (utilise uniquement un \"id\" de cette liste, ou null):
{catalog}
"""
    try:
        parsed = _run_agent_choice_llm(user_prompt)
    except Exception as e:
        logger.warning("[AssistantTriggerSetup] Échec appel LLM sélection agent: %s", e)
        return None

    agent_id = parsed.get("agent_id")
    if agent_id is None:
        logger.info("[AssistantTriggerSetup] LLM: aucun agent (null)")
        return None
    try:
        agent_id_int = int(agent_id)
    except (TypeError, ValueError):
        logger.warning("[AssistantTriggerSetup] agent_id invalide: %r", agent_id)
        return None
    if agent_id_int not in valid_ids:
        logger.warning(
            "[AssistantTriggerSetup] agent_id %s hors liste autorisée %s",
            agent_id_int,
            valid_ids,
        )
        return None

    agent = get_agent_by_id(db, agent_id_int, user_id)
    if not agent:
        return None
    return agent


def auto_create_triggers_for_leaves(
    db: Session,
    user_id: int,
    user_text: str,
    created_nodes: List[Dict[str, Any]],
    existing_nodes: list,
) -> List[Dict[str, Any]]:
    """
    Pour chaque feuille retenue du lot ``created_nodes``, sélectionne un agent (LLM) et crée un trigger
    (``cron`` si le texte décrit une récurrence et que la feuille correspond à un nœud « agent / veille »,
    sinon ``manual``). ``output_type`` : ``mindmap_child`` par défaut, ou ``email`` / ``audio_email`` si
    le texte utilisateur le permet (voir ``infer_output_delivery_from_text``).

    Si une planification est détectée mais que plusieurs feuilles existent (découpage trop fin par le modèle),
    un **seul** trigger est créé sur la feuille la plus alignée avec le texte utilisateur.

    Les erreurs sur un nœud n'interrompent pas les autres.
    """
    if not created_nodes:
        return []

    leaf_ids = find_leaf_node_ids(created_nodes)
    if not leaf_ids:
        return []

    schedule = parse_recurring_schedule_french(user_text)
    if schedule:
        logger.info(
            "[AssistantTriggerSetup] Planification détectée dans le texte: jours=%s %02d:%02d",
            schedule["cron_days"],
            schedule["cron_hour"],
            schedule["cron_minute"],
        )

    nodes_by_id = {n["id"]: n for n in created_nodes}
    orm_by_id = {getattr(n, "id", None): n for n in existing_nodes if getattr(n, "id", None) is not None}

    target_leaf_ids = _filter_leaves_for_scheduled_single_job(
        leaf_ids, schedule, nodes_by_id, orm_by_id, user_text
    )

    delivery = infer_output_delivery_from_text(user_text)
    out_type = delivery.get("output_type") or "mindmap_child"
    mail_to = delivery.get("email_to")
    mail_subj = delivery.get("email_subject")
    if out_type in ("email", "audio_email") and not mail_to:
        out_type = "mindmap_child"
        mail_to = None
        mail_subj = None

    created_triggers: List[Dict[str, Any]] = []

    for leaf_id in target_leaf_ids:
        node_info = nodes_by_id.get(leaf_id, {})
        label = node_info.get("label") or ""
        description = ""
        orm_node = orm_by_id.get(leaf_id)
        if orm_node is not None:
            description = getattr(orm_node, "description", None) or ""

        context = f"{user_text}\n\nNœud: {label}\nDescription: {description}".strip()

        try:
            agent = select_best_agent(db, user_id, context)
            if agent is None:
                logger.info(
                    "[AssistantTriggerSetup] Feuille %s (%s): pas d'agent retenu",
                    leaf_id,
                    label,
                )
                continue

            use_cron = _should_use_cron_for_leaf(schedule, target_leaf_ids, label, description)
            trigger_type = "cron" if use_cron else "manual"
            config = _build_trigger_config_base(
                agent.id,
                use_cron=use_cron,
                schedule=schedule,
                output_type=out_type,
                email_to=mail_to,
                email_subject=mail_subj,
            )

            trigger_data = TriggerCreate(
                node_id=leaf_id,
                trigger_type=trigger_type,
                enabled=True,
                config=config,
            )
            db_trigger = create_trigger(db, trigger_data, user_id)
            if db_trigger:
                created_triggers.append(
                    {
                        "node_id": leaf_id,
                        "trigger_id": db_trigger.id,
                        "agent_id": agent.id,
                        "agent_name": agent.name,
                    }
                )
            else:
                logger.warning(
                    "[AssistantTriggerSetup] create_trigger a retourné None pour nœud %s",
                    leaf_id,
                )
        except Exception as e:
            logger.error(
                "[AssistantTriggerSetup] Erreur trigger pour feuille %s: %s",
                leaf_id,
                e,
                exc_info=True,
            )

    return created_triggers
