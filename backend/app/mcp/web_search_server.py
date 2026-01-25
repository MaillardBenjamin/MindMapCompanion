"""
Serveur MCP (Model Context Protocol) pour la recherche web.

Ce serveur expose les outils de recherche web via le protocole MCP,
permettant aux agents d'utiliser ces outils de manière standardisée.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.services.web_search import get_web_search_service
from app.api.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/mcp/web-search", 
    tags=["MCP Web Search"],
    dependencies=[Depends(get_current_user)]
)


# Schémas MCP
class MCPTool(BaseModel):
    """Outil MCP"""
    name: str
    description: str
    inputSchema: Dict[str, Any]


class MCPToolCall(BaseModel):
    """Appel d'outil MCP"""
    name: str
    arguments: Dict[str, Any]


class MCPToolResult(BaseModel):
    """Résultat d'appel d'outil MCP"""
    content: List[Dict[str, Any]]
    isError: bool = False


# Outils MCP disponibles
MCP_TOOLS = [
    {
        "name": "web_search",
        "description": "Effectue une recherche web sur internet pour trouver des informations récentes sur un sujet donné",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Terme de recherche"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Nombre de résultats à retourner (défaut: 10, max: 50)",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50
                },
                "language": {
                    "type": "string",
                    "description": "Code langue (fr, en, etc.) - défaut: fr",
                    "default": "fr"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "web_search_news",
        "description": "Recherche d'actualités récentes sur internet (dernières 24-48h)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Terme de recherche pour les actualités"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Nombre de résultats à retourner (défaut: 10, max: 50)",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50
                },
                "language": {
                    "type": "string",
                    "description": "Code langue (fr, en, etc.) - défaut: fr",
                    "default": "fr"
                }
            },
            "required": ["query"]
        }
    }
]


@router.get("/tools", response_model=List[MCPTool])
async def list_tools():
    """
    Liste tous les outils disponibles sur ce serveur MCP.
    
    Returns:
        Liste des outils MCP disponibles
    """
    return [MCPTool(**tool) for tool in MCP_TOOLS]


@router.post("/tools/call", response_model=MCPToolResult)
async def call_tool(tool_call: MCPToolCall):
    """
    Appelle un outil MCP.
    
    Args:
        tool_call: Appel d'outil avec nom et arguments
    
    Returns:
        Résultat de l'appel d'outil
    """
    try:
        service = get_web_search_service()
        
        if tool_call.name == "web_search":
            query = tool_call.arguments.get("query", "")
            num_results = tool_call.arguments.get("num_results", 10)
            language = tool_call.arguments.get("language", "fr")
            
            results = service.search(
                query=query,
                num_results=min(num_results, 50),
                language=language,
            )
            
            return MCPToolResult(
                content=[
                    {
                        "type": "text",
                        "text": json.dumps({
                            "query": query,
                            "num_results": len(results),
                            "results": [r.to_dict() for r in results],
                        }, ensure_ascii=False, indent=2)
                    }
                ],
                isError=False,
            )
        
        elif tool_call.name == "web_search_news":
            query = tool_call.arguments.get("query", "")
            num_results = tool_call.arguments.get("num_results", 10)
            language = tool_call.arguments.get("language", "fr")
            
            results = service.search_news(
                query=query,
                num_results=min(num_results, 50),
                language=language,
            )
            
            return MCPToolResult(
                content=[
                    {
                        "type": "text",
                        "text": json.dumps({
                            "query": query,
                            "num_results": len(results),
                            "results": [r.to_dict() for r in results],
                        }, ensure_ascii=False, indent=2)
                    }
                ],
                isError=False,
            )
        
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Outil '{tool_call.name}' non trouvé"
            )
    
    except Exception as e:
        logger.error(f"Erreur lors de l'appel de l'outil {tool_call.name}: {e}")
        return MCPToolResult(
            content=[
                {
                    "type": "text",
                    "text": json.dumps({
                        "error": str(e),
                        "tool": tool_call.name,
                    })
                }
            ],
            isError=True,
        )


@router.get("/health")
async def health_check():
    """Vérification de l'état du serveur MCP"""
    try:
        service = get_web_search_service()
        # Vérifier si au moins une API est configurée
        has_config = (
            (service.google_api_key and service.google_engine_id) or
            service.bing_api_key
        )
        
        return {
            "status": "healthy",
            "tools_available": len(MCP_TOOLS),
            "search_configured": has_config,
            "provider": service.provider,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }
