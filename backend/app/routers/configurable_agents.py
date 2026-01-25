"""
Routes REST pour les agents configurables.

Expose les endpoints pour:
- CRUD des agents configurables
- Exécution d'agents configurables avec texte d'entrée
- Consultation des logs d'exécution
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.configurable_agent import (
    ConfigurableAgentCreate,
    ConfigurableAgentUpdate,
    ConfigurableAgentOut,
    ConfigurableAgentListOut,
    AgentExecuteRequest,
    AgentExecuteResponse,
    AgentExecutionLogOut,
    AgentExecutionLogListOut,
)
from app.crud.configurable_agent import (
    get_agent_by_id,
    get_agent_by_slug,
    get_agents,
    create_agent,
    update_agent,
    delete_agent,
    get_agent_execution_logs,
)
from app.services.configurable_agent_service import configurable_agent_service
import logging

logger = logging.getLogger(__name__)


def _agent_to_dict(agent) -> dict:
    """Convertit un agent SQLAlchemy en dictionnaire, gérant l'absence de input_schema"""
    return {
        "id": agent.id,
        "user_id": agent.user_id,
        "name": agent.name,
        "slug": agent.slug,
        "description": agent.description,
        "markdown_config": agent.markdown_config,
        "prompt_template": agent.prompt_template,
        "input_schema": getattr(agent, "input_schema", None),  # Gérer l'absence de la colonne
        "output_schema": agent.output_schema,
        "tools": agent.tools,
        "mcp_servers": agent.mcp_servers,
        "persona": agent.persona,
        "instructions": agent.instructions,
        "is_active": agent.is_active,
        "is_public": agent.is_public,
        "created_at": agent.created_at,
        "updated_at": agent.updated_at,
    }


router = APIRouter(
    prefix="/configurable-agents",
    tags=["Agents Configurables"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=ConfigurableAgentListOut)
async def list_agents(
    skip: int = 0,
    limit: int = 100,
    include_public: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Liste tous les agents configurables disponibles.
    
    Retourne les agents de l'utilisateur ainsi que les agents publics.
    """
    try:
        agents = get_agents(
            db=db,
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            include_public=include_public,
        )
        return ConfigurableAgentListOut(
            agents=[ConfigurableAgentOut.model_validate(_agent_to_dict(agent)) for agent in agents]
        )
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des agents: {e}", exc_info=True)
        # Vérifier si c'est une erreur de colonne manquante
        error_msg = str(e).lower()
        if "input_schema" in error_msg or ("column" in error_msg and "does not exist" in error_msg):
            raise HTTPException(
                status_code=500,
                detail="La colonne 'input_schema' est manquante en base de données. Exécutez: alembic upgrade head"
            )
        raise


@router.get("/{agent_id}", response_model=ConfigurableAgentOut)
async def get_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Récupère un agent configurable par son ID.
    """
    agent = get_agent_by_id(db, agent_id, current_user.id)
    if not agent:
        raise HTTPException(
            status_code=404,
            detail="Agent configurable non trouvé ou vous n'êtes pas autorisé à y accéder"
        )
    return ConfigurableAgentOut.model_validate(_agent_to_dict(agent))


@router.get("/slug/{slug}", response_model=ConfigurableAgentOut)
async def get_agent_by_slug_endpoint(
    slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Récupère un agent configurable par son slug.
    """
    agent = get_agent_by_slug(db, slug, current_user.id)
    if not agent:
        raise HTTPException(
            status_code=404,
            detail="Agent configurable non trouvé ou vous n'êtes pas autorisé à y accéder"
        )
    return ConfigurableAgentOut.model_validate(_agent_to_dict(agent))


@router.post("", response_model=ConfigurableAgentOut)
async def create_agent_endpoint(
    agent: ConfigurableAgentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Crée un nouvel agent configurable.
    
    Le fichier markdown peut être fourni dans `markdown_config` et sera parsé automatiquement.
    Les champs suivants seront extraits du markdown si fourni:
    - name, slug, description, persona (depuis le frontmatter)
    - prompt_template (depuis la section "Prompt Template")
    - output_schema (depuis la section "Output Schema")
    - tools (depuis la section "Tools")
    - mcp_servers (depuis la section "MCP Servers")
    - instructions (depuis la section "Instructions")
    """
    try:
        db_agent = create_agent(
            db=db,
            agent=agent,
            user_id=current_user.id,
        )
        # Gérer l'absence de input_schema
        agent_dict = {
            "id": db_agent.id,
            "user_id": db_agent.user_id,
            "name": db_agent.name,
            "slug": db_agent.slug,
            "description": db_agent.description,
            "markdown_config": db_agent.markdown_config,
            "prompt_template": db_agent.prompt_template,
            "input_schema": getattr(db_agent, "input_schema", None),
            "output_schema": db_agent.output_schema,
            "tools": db_agent.tools,
            "mcp_servers": db_agent.mcp_servers,
            "persona": db_agent.persona,
            "instructions": db_agent.instructions,
            "is_active": db_agent.is_active,
            "is_public": db_agent.is_public,
            "created_at": db_agent.created_at,
            "updated_at": db_agent.updated_at,
        }
        return ConfigurableAgentOut.model_validate(agent_dict)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{agent_id}", response_model=ConfigurableAgentOut)
async def update_agent_endpoint(
    agent_id: int,
    agent_update: ConfigurableAgentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Met à jour un agent configurable.
    
    Seul le propriétaire peut modifier un agent.
    """
    try:
        db_agent = update_agent(
            db=db,
            agent_id=agent_id,
            user_id=current_user.id,
            agent_update=agent_update,
        )
        if not db_agent:
            raise HTTPException(
                status_code=404,
                detail="Agent configurable non trouvé"
            )
        # Gérer l'absence de input_schema
        agent_dict = {
            "id": db_agent.id,
            "user_id": db_agent.user_id,
            "name": db_agent.name,
            "slug": db_agent.slug,
            "description": db_agent.description,
            "markdown_config": db_agent.markdown_config,
            "prompt_template": db_agent.prompt_template,
            "input_schema": getattr(db_agent, "input_schema", None),
            "output_schema": db_agent.output_schema,
            "tools": db_agent.tools,
            "mcp_servers": db_agent.mcp_servers,
            "persona": db_agent.persona,
            "instructions": db_agent.instructions,
            "is_active": db_agent.is_active,
            "is_public": db_agent.is_public,
            "created_at": db_agent.created_at,
            "updated_at": db_agent.updated_at,
        }
        return ConfigurableAgentOut.model_validate(agent_dict)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{agent_id}")
async def delete_agent_endpoint(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Supprime un agent configurable.
    
    Seul le propriétaire peut supprimer un agent.
    """
    try:
        success = delete_agent(
            db=db,
            agent_id=agent_id,
            user_id=current_user.id,
        )
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Agent configurable non trouvé"
            )
        return {"success": True, "message": "Agent configurable supprimé avec succès"}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/{agent_id}/execute", response_model=AgentExecuteResponse)
async def execute_agent(
    agent_id: int,
    request: AgentExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Exécute un agent configurable avec le texte fourni.
    
    Le texte fourni dans `input_text` remplace `{{input_text}}` dans le prompt template.
    Le résultat est retourné selon le schéma de sortie défini, si disponible.
    
    Args:
        agent_id: ID de l'agent à exécuter
        input_text: Texte qui complète le prompt et spécialise la demande
        options: Options additionnelles pour l'exécution (seront injectées dans le template)
    
    Returns:
        Résultat de l'exécution avec la sortie brute et parsée
    """
    try:
        from datetime import datetime
        
        result = await configurable_agent_service.execute_agent(
            db=db,
            agent_id=agent_id,
            user_id=current_user.id,
            input_text=request.input_text,
            options=request.options,
        )
        
        # Récupérer le nom de l'agent pour la réponse
        agent = get_agent_by_id(db, agent_id, current_user.id)
        agent_name = agent.name if agent else f"Agent {agent_id}"
        
        return AgentExecuteResponse(
            success=result["success"],
            agent_id=result["agent_id"],
            agent_name=agent_name,
            input_text=result["input_text"],
            prompt_used=result["prompt_used"],
            output_raw=result.get("output_raw"),
            output_parsed=result.get("output_parsed"),
            error_message=result.get("error_message"),
            execution_time_ms=result.get("execution_time_ms"),
            created_at=datetime.now(),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'exécution de l'agent: {str(e)}"
        )


@router.post("/slug/{slug}/execute", response_model=AgentExecuteResponse)
async def execute_agent_by_slug(
    slug: str,
    request: AgentExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Exécute un agent configurable par son slug avec le texte fourni.
    
    Similaire à /{agent_id}/execute mais utilise le slug au lieu de l'ID.
    """
    # Récupérer l'agent par son slug
    agent = get_agent_by_slug(db, slug, current_user.id)
    if not agent:
        raise HTTPException(
            status_code=404,
            detail="Agent configurable non trouvé ou vous n'êtes pas autorisé à y accéder"
        )
    
    # Rediriger vers l'endpoint avec l'ID
    return await execute_agent(
        agent_id=agent.id,
        request=request,
        db=db,
        current_user=current_user,
    )


@router.get("/{agent_id}/logs", response_model=AgentExecutionLogListOut)
async def get_agent_logs(
    agent_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Récupère les logs d'exécution d'un agent configurable.
    
    Seul le propriétaire peut consulter les logs de ses agents.
    """
    # Vérifier que l'agent existe et appartient à l'utilisateur
    agent = get_agent_by_id(db, agent_id, current_user.id)
    if not agent or agent.user_id != current_user.id:
        raise HTTPException(
            status_code=404,
            detail="Agent configurable non trouvé ou vous n'êtes pas autorisé à consulter ses logs"
        )
    
    logs = get_agent_execution_logs(
        db=db,
        agent_id=agent_id,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    
    return AgentExecutionLogListOut(
        logs=[
            AgentExecutionLogOut(
                id=log.id,
                agent_id=log.agent_id,
                agent_name=agent.name,
                user_id=log.user_id,
                input_text=log.input_text,
                prompt_used=log.prompt_used,
                output_raw=log.output_raw,
                output_parsed=log.output_parsed,
                success=log.success,
                error_message=log.error_message,
                execution_time_ms=log.execution_time_ms,
                created_at=log.created_at,
            )
            for log in logs
        ]
    )


@router.get("/logs/my", response_model=AgentExecutionLogListOut)
async def get_my_logs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Récupère tous les logs d'exécution de l'utilisateur pour tous ses agents.
    """
    logs = get_agent_execution_logs(
        db=db,
        agent_id=None,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    
    # Récupérer les noms des agents
    agent_ids = {log.agent_id for log in logs}
    agents = {agent.id: agent.name for agent in get_agents(db, user_id=current_user.id, include_public=False)}
    
    return AgentExecutionLogListOut(
        logs=[
            AgentExecutionLogOut(
                id=log.id,
                agent_id=log.agent_id,
                agent_name=agents.get(log.agent_id, f"Agent {log.agent_id}"),
                user_id=log.user_id,
                input_text=log.input_text,
                prompt_used=log.prompt_used,
                output_raw=log.output_raw,
                output_parsed=log.output_parsed,
                success=log.success,
                error_message=log.error_message,
                execution_time_ms=log.execution_time_ms,
                created_at=log.created_at,
            )
            for log in logs
        ]
    )
