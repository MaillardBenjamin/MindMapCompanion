"""
Outils pour la recherche web.
Ces outils peuvent être utilisés par les agents configurables.
"""

import logging
from typing import List, Dict, Any, Optional

from app.services.web_search import get_web_search_service

logger = logging.getLogger(__name__)


def web_search_tool(query: str, num_results: int = 10, language: str = "fr") -> Dict[str, Any]:
    """
    Effectue une recherche web sur internet.
    
    Args:
        query: Terme de recherche
        num_results: Nombre de résultats à retourner (défaut: 10, max: 50)
        language: Code langue (fr, en, etc.) - défaut: fr
    
    Returns:
        Dictionnaire avec les résultats de recherche
    """
    try:
        service = get_web_search_service()
        results = service.search(
            query=query,
            num_results=min(num_results, 50),
            language=language,
        )
        
        return {
            "success": True,
            "query": query,
            "num_results": len(results),
            "results": [r.to_dict() for r in results],
        }
    except Exception as e:
        logger.error(f"Erreur dans web_search_tool: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "results": [],
        }


def web_search_news_tool(query: str, num_results: int = 10, language: str = "fr") -> Dict[str, Any]:
    """
    Recherche d'actualités récentes sur internet.
    
    Args:
        query: Terme de recherche
        num_results: Nombre de résultats à retourner (défaut: 10, max: 50)
        language: Code langue (fr, en, etc.) - défaut: fr
    
    Returns:
        Dictionnaire avec les résultats d'actualités
    """
    try:
        service = get_web_search_service()
        results = service.search_news(
            query=query,
            num_results=min(num_results, 50),
            language=language,
        )
        
        return {
            "success": True,
            "query": query,
            "num_results": len(results),
            "results": [r.to_dict() for r in results],
        }
    except Exception as e:
        logger.error(f"Erreur dans web_search_news_tool: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "results": [],
        }


def get_web_search_tools() -> List[Dict[str, Any]]:
    """
    Retourne la liste des outils de recherche web disponibles.
    
    Returns:
        Liste de dictionnaires décrivant les outils
    """
    return [
        {
            "name": "web_search",
            "description": "Effectue une recherche web sur internet pour trouver des informations récentes. Utilise cet outil pour rechercher des informations sur un sujet spécifique.",
            "function": web_search_tool,
            "args": {
                "query": {
                    "type": "string",
                    "description": "Terme de recherche",
                    "required": True,
                },
                "num_results": {
                    "type": "integer",
                    "description": "Nombre de résultats à retourner (défaut: 10, max: 50)",
                    "required": False,
                    "default": 10,
                },
                "language": {
                    "type": "string",
                    "description": "Code langue (fr, en, etc.) - défaut: fr",
                    "required": False,
                    "default": "fr",
                },
            },
        },
        {
            "name": "web_search_news",
            "description": "Recherche d'actualités récentes sur internet. Utilise cet outil pour trouver les dernières nouvelles sur un sujet spécifique.",
            "function": web_search_news_tool,
            "args": {
                "query": {
                    "type": "string",
                    "description": "Terme de recherche",
                    "required": True,
                },
                "num_results": {
                    "type": "integer",
                    "description": "Nombre de résultats à retourner (défaut: 10, max: 50)",
                    "required": False,
                    "default": 10,
                },
                "language": {
                    "type": "string",
                    "description": "Code langue (fr, en, etc.) - défaut: fr",
                    "required": False,
                    "default": "fr",
                },
            },
        },
    ]


# Mapping des noms d'outils vers les fonctions
TOOL_FUNCTIONS = {
    "web_search": web_search_tool,
    "web_search_news": web_search_news_tool,
}
