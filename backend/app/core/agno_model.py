"""
Création du modèle de chat Agno : OpenAI ou Ollama (local).

Si OLLAMA_BASE_URL est défini dans la config, le modèle pointe vers Ollama.
Sinon, utilisation d'OpenAI (AGNO_API_KEY ou OPENAI_API_KEY).
"""

import logging

from agno.models.openai import OpenAIChat

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def get_agno_chat_model() -> OpenAIChat:
    """
    Retourne une instance OpenAIChat configurée pour Ollama ou OpenAI.

    - Ollama : lorsque OLLAMA_BASE_URL est défini (ex: http://localhost:11434/v1),
      utilise ce serveur avec AGNO_MODEL (ex: qwen3:14b). Aucune clé API requise.
    - OpenAI : sinon utilise AGNO_API_KEY ou OPENAI_API_KEY.
    """
    settings = get_settings()
    if settings.ollama_base_url:
        base = settings.ollama_base_url.strip().rstrip("/")
        if not base.endswith("/v1"):
            base = f"{base}/v1"
        logger.info(
            "Modèle Agno instancié: provider=Ollama | model=%s | base_url=%s",
            settings.agno_model,
            base,
        )
        return OpenAIChat(
            id=settings.agno_model,
            api_key="ollama",
            base_url=base,
        )
    api_key = settings.agno_api_key or settings.openai_api_key
    logger.info(
        "Modèle Agno instancié: provider=OpenAI | model=%s",
        settings.agno_model,
    )
    return OpenAIChat(
        id=settings.agno_model,
        api_key=api_key,
    )


def is_ollama_configured() -> bool:
    """Indique si Ollama est configuré (OLLAMA_BASE_URL non vide)."""
    return bool(get_settings().ollama_base_url)
