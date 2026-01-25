"""
CRUD operations pour les agents configurables.
"""

import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, inspect

from app.models.configurable_agent import ConfigurableAgent, AgentExecutionLog
from app.schemas.configurable_agent import ConfigurableAgentCreate, ConfigurableAgentUpdate
from app.services.agent_config_parser import AgentConfigParser

logger = logging.getLogger(__name__)


def _has_input_schema_column(db: Session) -> bool:
    """Vérifie si la colonne input_schema existe dans la table configurable_agents"""
    try:
        inspector = inspect(db.bind)
        columns = [col['name'] for col in inspector.get_columns('configurable_agents')]
        return 'input_schema' in columns
    except Exception as e:
        logger.warning(f"Impossible de vérifier l'existence de la colonne input_schema: {e}")
        return False


def get_agent_by_id(db: Session, agent_id: int, user_id: Optional[int] = None) -> Optional[ConfigurableAgent]:
    """Récupère un agent par son ID"""
    query = db.query(ConfigurableAgent).filter(ConfigurableAgent.id == agent_id)
    
    # Si user_id est fourni, vérifier que l'agent appartient à l'utilisateur ou est public
    if user_id:
        query = query.filter(
            or_(
                ConfigurableAgent.user_id == user_id,
                ConfigurableAgent.is_public == True
            )
        )
    
    return query.first()


def get_agent_by_slug(db: Session, slug: str, user_id: Optional[int] = None) -> Optional[ConfigurableAgent]:
    """Récupère un agent par son slug"""
    query = db.query(ConfigurableAgent).filter(
        ConfigurableAgent.slug == slug,
        ConfigurableAgent.is_active == True,
    )
    
    # Si user_id est fourni, vérifier que l'agent appartient à l'utilisateur ou est public
    if user_id:
        query = query.filter(
            or_(
                ConfigurableAgent.user_id == user_id,
                ConfigurableAgent.is_public == True
            )
        )
    
    return query.first()


def get_agents(
    db: Session,
    user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    include_public: bool = True,
) -> List[ConfigurableAgent]:
    """Récupère la liste des agents configurables"""
    query = db.query(ConfigurableAgent).filter(ConfigurableAgent.is_active == True)
    
    if user_id:
        if include_public:
            # Récupérer les agents de l'utilisateur et les agents publics
            query = query.filter(
                or_(
                    ConfigurableAgent.user_id == user_id,
                    ConfigurableAgent.is_public == True
                )
            )
        else:
            # Seulement les agents de l'utilisateur
            query = query.filter(ConfigurableAgent.user_id == user_id)
    else:
        # Sans user_id, retourner seulement les agents publics
        query = query.filter(ConfigurableAgent.is_public == True)
    
    return query.offset(skip).limit(limit).all()


def create_agent(
    db: Session,
    agent: ConfigurableAgentCreate,
    user_id: int,
) -> ConfigurableAgent:
    """Crée un nouvel agent configurable"""
    parser = AgentConfigParser()
    
    # Si markdown_config est fourni, le parser
    if agent.markdown_config:
        parsed_config = parser.parse_markdown(agent.markdown_config)
        
        # Valider la configuration parsée
        is_valid, error = parser.validate_config(parsed_config)
        if not is_valid:
            raise ValueError(f"Configuration invalide: {error}")
        
        # Utiliser les valeurs parsées si elles ne sont pas déjà définies
        if not agent.name and parsed_config.get("name"):
            agent.name = parsed_config["name"]
        if not agent.slug and parsed_config.get("slug"):
            agent.slug = parsed_config["slug"]
        if not agent.description and parsed_config.get("description"):
            agent.description = parsed_config["description"]
        if not agent.persona and parsed_config.get("persona"):
            agent.persona = parsed_config["persona"]
        if not agent.prompt_template and parsed_config.get("prompt_template"):
            agent.prompt_template = parsed_config["prompt_template"]
        if not agent.input_schema and parsed_config.get("input_schema"):
            agent.input_schema = parsed_config["input_schema"]
        if not agent.output_schema and parsed_config.get("output_schema"):
            agent.output_schema = parsed_config["output_schema"]
        if not agent.tools and parsed_config.get("tools"):
            agent.tools = parsed_config["tools"]
        if not agent.mcp_servers and parsed_config.get("mcp_servers"):
            agent.mcp_servers = parsed_config["mcp_servers"]
        if not agent.instructions and parsed_config.get("instructions"):
            agent.instructions = parsed_config["instructions"]
    
    # Vérifier que le slug est unique pour cet utilisateur
    existing = get_agent_by_slug(db, agent.slug, user_id)
    if existing:
        raise ValueError(f"Un agent avec le slug '{agent.slug}' existe déjà pour cet utilisateur")
    
    db_agent = ConfigurableAgent(
        user_id=user_id,
        name=agent.name,
        slug=agent.slug,
        description=agent.description,
        markdown_config=agent.markdown_config,
        prompt_template=agent.prompt_template,
        input_schema=agent.input_schema,
        output_schema=agent.output_schema,
        tools=agent.tools or [],
        mcp_servers=agent.mcp_servers or [],
        persona=agent.persona,
        instructions=agent.instructions,
        is_active=agent.is_active,
        is_public=agent.is_public,
    )
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return db_agent


def update_agent(
    db: Session,
    agent_id: int,
    user_id: int,
    agent_update: ConfigurableAgentUpdate,
) -> Optional[ConfigurableAgent]:
    """Met à jour un agent configurable"""
    db_agent = get_agent_by_id(db, agent_id, user_id)
    if not db_agent:
        return None
    
    # Vérifier que l'utilisateur est propriétaire
    if db_agent.user_id != user_id:
        raise PermissionError("Vous n'êtes pas autorisé à modifier cet agent")
    
    parser = AgentConfigParser()
    
    # Si markdown_config est fourni, le parser
    if agent_update.markdown_config is not None:
        parsed_config = parser.parse_markdown(agent_update.markdown_config)
        
        # Valider la configuration parsée
        is_valid, error = parser.validate_config(parsed_config)
        if not is_valid:
            raise ValueError(f"Configuration invalide: {error}")
        
        # Mettre à jour avec les valeurs parsées
        update_dict = agent_update.model_dump(exclude_unset=True)
        for key, value in parsed_config.items():
            if key not in update_dict or update_dict[key] is None:
                update_dict[key] = value
        
        agent_update = ConfigurableAgentUpdate(**update_dict)
    
    # Vérifier l'unicité du slug si changé
    if agent_update.slug and agent_update.slug != db_agent.slug:
        existing = get_agent_by_slug(db, agent_update.slug)
        if existing and existing.id != agent_id:
            raise ValueError(f"Un agent avec le slug '{agent_update.slug}' existe déjà")
    
    # Mettre à jour les champs
    update_dict = agent_update.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(db_agent, key, value)
    
    db.commit()
    db.refresh(db_agent)
    return db_agent


def delete_agent(db: Session, agent_id: int, user_id: int) -> bool:
    """Supprime un agent configurable"""
    db_agent = get_agent_by_id(db, agent_id, user_id)
    if not db_agent:
        return False
    
    # Vérifier que l'utilisateur est propriétaire
    if db_agent.user_id != user_id:
        raise PermissionError("Vous n'êtes pas autorisé à supprimer cet agent")
    
    db.delete(db_agent)
    db.commit()
    return True


def get_agent_execution_logs(
    db: Session,
    agent_id: Optional[int] = None,
    user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[AgentExecutionLog]:
    """Récupère les logs d'exécution d'agents"""
    query = db.query(AgentExecutionLog)
    
    if agent_id:
        query = query.filter(AgentExecutionLog.agent_id == agent_id)
    
    if user_id:
        query = query.filter(AgentExecutionLog.user_id == user_id)
    
    return query.order_by(AgentExecutionLog.created_at.desc()).offset(skip).limit(limit).all()
