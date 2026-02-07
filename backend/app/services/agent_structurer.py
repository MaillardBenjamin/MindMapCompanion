import json
import re
from typing import Any

from app.core.config import get_settings

settings = get_settings()


SYSTEM_PROMPT = """
Tu es l'agent StructurerMindmap. Tu dois renvoyer UNIQUEMENT un JSON strict.
Respecte le schéma demandé et n'ajoute aucun texte hors JSON.
"""


def _extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _build_agent():
    from app.core.agno_model import get_agno_chat_model, is_ollama_configured
    if not is_ollama_configured() and not settings.agno_api_key and not settings.openai_api_key:
        raise RuntimeError("AGNO_API_KEY/OPENAI_API_KEY manquant, ou configurez OLLAMA_BASE_URL pour Ollama.")
    try:
        from agno.agent import Agent
    except Exception as exc:  # pragma: no cover - dépendance externe
        raise RuntimeError("Agno non disponible dans l'environnement.") from exc

    model = get_agno_chat_model()
    return Agent(model=model, instructions=[SYSTEM_PROMPT])


def run_structurer_mindmap(raw_text: str, context: list[dict[str, Any]]) -> dict:
    agent = _build_agent()
    prompt = {
        "raw_text": raw_text,
        "context_nodes": context,
        "schema": {
            "title": "string",
            "type": "idea|task|note|project|event",
            "domain": "string",
            "tags": ["string"],
            "links": [
                {
                    "toNodeId": "uuid",
                    "relationType": "related|parent|depends_on|mentions|reference",
                    "confidence": 0.0,
                }
            ],
            "placement": {"parentNodeId": "uuid|null", "branchLabel": "string|null"},
            "nextAction": "string|null",
            "confidence": 0.0,
            "rationale": ["string"],
        },
    }
    result = agent.run(
        f"{SYSTEM_PROMPT}\nRetourne un JSON strict pour cette entrée:\n{json.dumps(prompt, ensure_ascii=False)}"
    )
    content = getattr(result, "content", None) or getattr(result, "output", None) or result
    return _extract_json(str(content))
