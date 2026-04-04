"""Création d'un nœud enfant à partir de la sortie d'un agent (rendu markdown)."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session

from app.crud.mindmap import create_node
from app.models.mindmap import Node
from app.schemas.mindmap import NodeCreate

logger = logging.getLogger(__name__)

_IMPORTANCE_FR: Dict[str, str] = {
    "high": "élevée",
    "medium": "moyenne",
    "low": "faible",
}
_DIRECTION_FR: Dict[str, str] = {
    "emerging": "émergente",
    "growing": "en croissance",
    "declining": "en déclin",
    "stable": "stable",
}
_PRIORITY_FR: Dict[str, str] = {
    "urgent": "urgente",
    "high": "élevée",
    "medium": "moyenne",
    "low": "faible",
}
_RELIABILITY_FR: Dict[str, str] = {
    "high": "élevée",
    "medium": "moyenne",
    "low": "faible",
}
_TYPE_FR: Dict[str, str] = {
    "news": "actualité",
    "blog": "blog",
    "social": "réseau social",
    "official": "officiel",
    "research": "recherche",
    "other": "autre",
}

_SECTION_HEADING = re.compile(
    r"^\s*(theme|executive_summary|key_findings|trends|sources|recommendations|next_steps|report_date|rapport_date)\s*$",
    re.MULTILINE | re.IGNORECASE,
)


def _parse_yaml_like_block(text: str, allowed: Set[str]) -> Dict[str, str]:
    """Parse un bloc « clef: valeur » ; les lignes suivantes sans clef prolongent la dernière clef."""
    result: Dict[str, str] = {}
    current: Optional[str] = None
    key_re = re.compile(r"^(\w+):\s*(.*)$")
    for line in text.split("\n"):
        m = key_re.match(line)
        if m and m.group(1).lower() in allowed:
            if current is not None:
                result[current] = result[current].strip()
            k = m.group(1).lower()
            v = m.group(2).strip()
            current = k
            result[k] = v
        elif current is not None:
            result[current] = (result[current] + "\n" + line).strip()
    if current is not None:
        result[current] = result[current].strip()
    return result


def _parse_key_findings_plain(body: str) -> List[Dict[str, str]]:
    chunks = re.split(r"\n(?=\s*title:\s*)", body.strip(), flags=re.IGNORECASE)
    allowed = {"title", "description", "importance", "source", "date"}
    out: List[Dict[str, str]] = []
    for ch in chunks:
        ch = ch.strip()
        if not ch:
            continue
        d = _parse_yaml_like_block(ch, allowed)
        if d:
            out.append(d)
    return out


def _split_and_parse_items(body: str, first_field: str, allowed: Set[str]) -> List[Dict[str, str]]:
    pat = rf"\n(?=\s*{re.escape(first_field)}:\s*)"
    chunks = re.split(pat, body.strip(), flags=re.IGNORECASE)
    out: List[Dict[str, str]] = []
    for ch in chunks:
        ch = ch.strip()
        if not ch:
            continue
        d = _parse_yaml_like_block(ch, allowed)
        if d:
            out.append(d)
    return out


def parse_news_monitor_plaintext(raw: str) -> Optional[Dict[str, Any]]:
    """
    Interprète une sortie modèle du type :

        theme

        …
        executive_summary

        …
        key_findings
        title: …
        description: …

    (sans JSON), pour produire le même dictionnaire que le schéma JSON News Monitor.
    """
    if not raw or not raw.strip():
        return None
    if not _SECTION_HEADING.search(raw):
        return None
    parts = _SECTION_HEADING.split(raw)
    result: Dict[str, Any] = {}
    i = 1
    while i + 1 < len(parts):
        key = parts[i].lower()
        body = parts[i + 1].strip()
        i += 2
        if key == "rapport_date":
            key = "report_date"
        if key == "theme":
            result["theme"] = body
        elif key == "executive_summary":
            result["executive_summary"] = body
        elif key == "key_findings":
            kf = _parse_key_findings_plain(body)
            if kf:
                result["key_findings"] = kf
        elif key == "trends":
            items = _split_and_parse_items(
                body, "trend_name", {"trend_name", "description", "direction", "impact"}
            )
            if items:
                result["trends"] = items
        elif key == "sources":
            items = _split_and_parse_items(
                body, "name", {"name", "url", "reliability", "type"}
            )
            if items:
                result["sources"] = items
        elif key == "recommendations":
            items = _split_and_parse_items(
                body, "action", {"action", "rationale", "priority"}
            )
            if items:
                result["recommendations"] = items
        elif key == "next_steps":
            result["next_steps"] = body
        elif key == "report_date":
            result["report_date"] = body
    return result if result else None


def _should_render_news_monitor_markdown(parsed: Dict[str, Any]) -> bool:
    if isinstance(parsed.get("executive_summary"), str) and parsed["executive_summary"].strip():
        return True
    kf = parsed.get("key_findings")
    if isinstance(kf, list) and len(kf) > 0:
        return True
    tr = parsed.get("trends")
    if isinstance(tr, list) and len(tr) > 0:
        return True
    src = parsed.get("sources")
    if isinstance(src, list) and len(src) > 0:
        return True
    rec = parsed.get("recommendations")
    if isinstance(rec, list) and len(rec) > 0:
        return True
    ns = parsed.get("next_steps")
    if isinstance(ns, str) and ns.strip():
        return True
    rd = parsed.get("report_date") or parsed.get("rapport_date")
    if isinstance(rd, str) and rd.strip():
        return True
    return False


def _news_monitor_parsed_to_markdown(parsed: Dict[str, Any]) -> str:
    parts: List[str] = []

    theme = parsed.get("theme")
    if isinstance(theme, str) and theme.strip():
        parts.append(f"## {theme.strip()}\n\n")

    es = parsed.get("executive_summary")
    if isinstance(es, str) and es.strip():
        parts.extend(["### Résumé exécutif\n\n", es.strip(), "\n\n"])

    kf = parsed.get("key_findings")
    if isinstance(kf, list) and kf:
        parts.append("### Points clés\n\n")
        for item in kf:
            if not isinstance(item, dict):
                continue
            title = (item.get("title") or "").strip()
            body = (item.get("description") or item.get("summary") or "").strip()
            if title:
                parts.append(f"- **{title}**")
            elif body:
                parts.append("- *(Sans titre)*")
            if body:
                parts.append(f"\n\n  {body.replace(chr(10), chr(10) + '  ')}\n")
            elif title:
                parts.append("\n")
            meta: List[str] = []
            imp = item.get("importance")
            if isinstance(imp, str) and imp.strip():
                meta.append(f"Importance : {_IMPORTANCE_FR.get(imp.strip(), imp.strip())}")
            src = item.get("source")
            if isinstance(src, str) and src.strip():
                meta.append(f"Source : {src.strip()}")
            dt = item.get("date")
            if isinstance(dt, str) and dt.strip():
                meta.append(f"Date : {dt.strip()}")
            if meta:
                parts.append(f"  \n  *{' · '.join(meta)}*\n")
            parts.append("\n")

    trends = parsed.get("trends")
    if isinstance(trends, list) and trends:
        parts.append("### Tendances\n\n")
        for item in trends:
            if not isinstance(item, dict):
                continue
            name = (item.get("trend_name") or "").strip()
            desc = (item.get("description") or "").strip()
            if name:
                parts.append(f"- **{name}**")
            elif desc:
                parts.append("- *(Sans titre)*")
            if desc:
                parts.append(f"\n\n  {desc.replace(chr(10), chr(10) + '  ')}\n")
            elif name:
                parts.append("\n")
            meta2: List[str] = []
            direction = item.get("direction")
            if isinstance(direction, str) and direction.strip():
                meta2.append(
                    f"Direction : {_DIRECTION_FR.get(direction.strip(), direction.strip())}"
                )
            impact = item.get("impact")
            if isinstance(impact, str) and impact.strip():
                meta2.append(f"Impact : {impact.strip()}")
            if meta2:
                parts.append(f"  \n  *{' · '.join(meta2)}*\n")
            parts.append("\n")

    sources = parsed.get("sources")
    if isinstance(sources, list) and sources:
        parts.append("### Sources\n\n")
        for item in sources:
            if not isinstance(item, dict):
                continue
            name = (item.get("name") or "").strip()
            url = (item.get("url") or "").strip()
            rel = item.get("reliability")
            typ = item.get("type")
            line = f"- **{name}**" if name else "- *(sans nom)*"
            extras: List[str] = []
            if isinstance(typ, str) and typ.strip():
                extras.append(_TYPE_FR.get(typ.strip(), typ.strip()))
            if isinstance(rel, str) and rel.strip():
                extras.append(f"fiabilité : {_RELIABILITY_FR.get(rel.strip(), rel.strip())}")
            if extras:
                line += f" — {', '.join(extras)}"
            parts.append(line + "\n")
            if url:
                parts.append(f"  - {url}\n")
        parts.append("\n")

    recs = parsed.get("recommendations")
    if isinstance(recs, list) and recs:
        parts.append("### Recommandations\n\n")
        for item in recs:
            if not isinstance(item, dict):
                continue
            action = (item.get("action") or "").strip()
            rationale = (item.get("rationale") or "").strip()
            pri = item.get("priority")
            pri_fr = ""
            if isinstance(pri, str) and pri.strip():
                pri_fr = f" *(priorité : {_PRIORITY_FR.get(pri.strip(), pri.strip())})*"
            if action:
                parts.append(f"- **{action}**{pri_fr}\n")
            if rationale:
                parts.append(f"  - {rationale.replace(chr(10), chr(10) + '  - ')}\n")
            parts.append("\n")

    ns = parsed.get("next_steps")
    if isinstance(ns, str) and ns.strip():
        parts.extend(["### Prochaines étapes\n\n", ns.strip(), "\n\n"])

    rd = parsed.get("report_date") or parsed.get("rapport_date")
    if isinstance(rd, str) and rd.strip():
        parts.append(f"*Date du rapport : {rd.strip()}*\n")

    return "".join(parts).strip()


def extract_markdown_from_agent_output(output: Optional[Dict[str, Any]]) -> Optional[str]:
    """Préfère le markdown explicite ou le rendu FR News Monitor, puis la sortie brute."""
    if not output:
        return None
    raw = (output.get("output_raw") or "").strip()
    parsed = output.get("output_parsed")
    if isinstance(parsed, dict):
        md = parsed.get("markdown")
        if isinstance(md, str) and md.strip():
            return md.strip()
        if _should_render_news_monitor_markdown(parsed):
            built = _news_monitor_parsed_to_markdown(parsed)
            if built:
                return built
    if raw:
        return raw
    if isinstance(parsed, dict):
        try:
            return "```json\n" + json.dumps(parsed, ensure_ascii=False, indent=2) + "\n```"
        except (TypeError, ValueError):
            return None
    return None


def create_child_from_agent_output(db: Session, parent: Node, output: Dict[str, Any]) -> Node:
    """Crée un nœud enfant sous `parent` avec le libellé « YYYY-MM-DD — titre du parent »."""
    md = extract_markdown_from_agent_output(output)
    if not md:
        raise ValueError("Aucun contenu markdown exploitable dans la sortie de l'agent")

    date_str = datetime.now().strftime("%Y-%m-%d")
    parent_title = (parent.label or "Sans titre").strip() or "Sans titre"
    label = f"{date_str} — {parent_title}"[:200]

    n_children = (
        db.query(Node)
        .filter(Node.parent_id == parent.id, Node.mindmap_id == parent.mindmap_id)
        .count()
    )

    node_create = NodeCreate(
        mindmap_id=parent.mindmap_id,
        parent_id=parent.id,
        label=label,
        description=md,
        color=parent.color or "#00D9FF",
        position_x=int(parent.position_x) + 200,
        position_y=int(parent.position_y) + n_children * 80,
        is_root=False,
        status="inbox",
    )
    child = create_node(db, node_create)
    logger.info(
        "[agent_result_child_node] Nœud enfant créé id=%s sous parent_id=%s",
        child.id,
        parent.id,
    )
    return child
