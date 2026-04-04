"""Création d'un nœud enfant à partir de la sortie d'un agent (rendu markdown)."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.crud.mindmap import create_node
from app.models.mindmap import Node
from app.schemas.mindmap import NodeCreate

logger = logging.getLogger(__name__)


def extract_markdown_from_agent_output(output: Optional[Dict[str, Any]]) -> Optional[str]:
    """Aligné sur la logique frontend (output_raw, puis output_parsed.markdown, etc.)."""
    if not output:
        return None
    raw = (output.get("output_raw") or "").strip()
    if raw:
        return raw
    parsed = output.get("output_parsed")
    if isinstance(parsed, dict):
        md = parsed.get("markdown")
        if isinstance(md, str) and md.strip():
            return md.strip()
        if isinstance(parsed.get("executive_summary"), str) or isinstance(
            parsed.get("key_findings"), list
        ):
            parts: List[str] = []
            theme = parsed.get("theme")
            if isinstance(theme, str):
                parts.append(f"## {theme}\n")
            es = parsed.get("executive_summary")
            if isinstance(es, str):
                parts.extend(["### Résumé exécutif\n\n", es, "\n\n"])
            kf = parsed.get("key_findings")
            if isinstance(kf, list):
                parts.append("### Points clés\n\n")
                for item in kf:
                    if isinstance(item, dict):
                        title = item.get("title") or ""
                        summary = item.get("summary") or ""
                        parts.append(f"- **{title}**{f': {summary}' if summary else ''}\n")
            built = "".join(parts).strip()
            if built:
                return built
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
