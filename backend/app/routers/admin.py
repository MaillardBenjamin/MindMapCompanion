from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from pathlib import Path

from app.api.deps import get_current_user
from app.db.session import get_async_session
from app.database import get_db
from app.models.event import Event
from app.models.execution_log import ExecutionLog
from app.models.user import User
from app.crud.configurable_agent import create_agent, get_agent_by_slug
from app.schemas.configurable_agent import ConfigurableAgentCreate
from app.services.agent_config_parser import AgentConfigParser

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_user)])


@router.get("/events")
async def list_events(session: AsyncSession = Depends(get_async_session)) -> dict:
    result = await session.execute(select(Event))
    return {"events": [e.payload | {"id": str(e.id), "event_id": str(e.event_id)} for e in result.scalars().all()]}


@router.post("/load-agents-from-files")
async def load_agents_from_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Charge automatiquement les agents configurables depuis les fichiers .md
    dans le répertoire app/agent_configs/agents/
    """
    import logging
    logger = logging.getLogger(__name__)
    
    agent_configs_dir = Path(__file__).parent.parent / "agent_configs"
    agents_dir = agent_configs_dir / "agents"
    loaded_agents = []
    errors = []
    
    logger.info(f"Chargement des agents depuis: {agents_dir}")
    logger.info(f"Répertoire existe: {agents_dir.exists()}")
    
    # Chercher tous les fichiers .md dans agents/ et aussi à la racine de agent_configs/ (rétrocompatibilité)
    md_files = []
    if agents_dir.exists():
        md_files.extend(list(agents_dir.glob("*.md")))
    if agent_configs_dir.exists():
        md_files.extend(list(agent_configs_dir.glob("*.md")))
    
    # Supprimer les doublons
    md_files = list(set(md_files))
    
    logger.info(f"Fichiers .md trouvés: {[f.name for f in md_files]}")
    
    if not md_files:
        errors.append(f"Aucun fichier .md trouvé dans {agents_dir} ou {agent_configs_dir}")
        logger.warning(f"Aucun fichier .md trouvé dans {agents_dir} ou {agent_configs_dir}")
    
    for md_file in md_files:
        logger.info(f"Traitement du fichier: {md_file.name}")
        try:
            # Lire le contenu du fichier
            with open(md_file, "r", encoding="utf-8") as f:
                markdown_content = f.read()
            
            # Parser le frontmatter pour obtenir le slug
            import re
            frontmatter_match = re.match(r'^---\n(.*?)\n---\n', markdown_content, re.DOTALL)
            if not frontmatter_match:
                errors.append(f"{md_file.name}: Pas de frontmatter trouvé")
                continue
            
            # Extraire le slug depuis le frontmatter
            frontmatter = frontmatter_match.group(1)
            slug_match = re.search(r'^slug:\s*(.+)$', frontmatter, re.MULTILINE)
            if not slug_match:
                errors.append(f"{md_file.name}: Pas de slug trouvé dans le frontmatter")
                continue
            
            slug = slug_match.group(1).strip()
            
            logger.info(f"Parsing du markdown pour l'agent {slug}")
            # Parser le markdown pour extraire tous les champs
            parser = AgentConfigParser()
            parsed_config = parser.parse_markdown(markdown_content)
            
            # Valider la configuration parsée
            is_valid, error = parser.validate_config(parsed_config)
            if not is_valid:
                errors.append(f"{md_file.name}: Configuration invalide - {error}")
                logger.error(f"Configuration invalide pour {md_file.name}: {error}")
                continue
            
            # Vérifier si l'agent existe déjà pour cet utilisateur
            existing_agent = get_agent_by_slug(db, slug, current_user.id)
            
            if existing_agent:
                # Mettre à jour l'agent existant avec les nouvelles valeurs
                logger.info(f"Mise à jour de l'agent {slug} (ID: {existing_agent.id})")
                existing_agent.name = parsed_config.get("name", existing_agent.name)
                existing_agent.description = parsed_config.get("description", existing_agent.description)
                existing_agent.persona = parsed_config.get("persona", existing_agent.persona)
                existing_agent.markdown_config = markdown_content
                existing_agent.prompt_template = parsed_config.get("prompt_template", "")
                existing_agent.input_schema = parsed_config.get("input_schema")
                existing_agent.output_schema = parsed_config.get("output_schema")
                existing_agent.tools = parsed_config.get("tools", [])
                existing_agent.mcp_servers = parsed_config.get("mcp_servers", [])
                existing_agent.instructions = parsed_config.get("instructions")
                db.commit()
                db.refresh(existing_agent)
                logger.info(f"Agent {slug} mis à jour avec succès (prompt_template: {len(existing_agent.prompt_template)} caractères, tools: {existing_agent.tools})")
                loaded_agents.append({
                    "slug": slug,
                    "status": "mis à jour",
                    "id": existing_agent.id,
                    "prompt_template_length": len(existing_agent.prompt_template),
                    "tools": existing_agent.tools,
                })
            else:
                logger.info(f"Création de l'agent {slug} pour l'utilisateur {current_user.id}")
                # Créer l'agent avec les valeurs parsées
                agent_create = ConfigurableAgentCreate(
                    name=parsed_config.get("name", ""),
                    slug=slug,
                    description=parsed_config.get("description"),
                    persona=parsed_config.get("persona"),
                    markdown_config=markdown_content,
                    prompt_template=parsed_config.get("prompt_template", ""),
                    input_schema=parsed_config.get("input_schema"),
                    output_schema=parsed_config.get("output_schema"),
                    tools=parsed_config.get("tools", []),
                    mcp_servers=parsed_config.get("mcp_servers", []),
                    instructions=parsed_config.get("instructions"),
                    is_active=True,
                    is_public=False,
                )
                
                agent = create_agent(db=db, agent=agent_create, user_id=current_user.id)
                logger.info(f"Agent {slug} créé avec succès (ID: {agent.id})")
                loaded_agents.append({
                    "slug": slug,
                    "status": "créé",
                    "id": agent.id,
                })
            
        except Exception as e:
            error_msg = f"{md_file.name}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"Erreur lors du traitement de {md_file.name}: {e}", exc_info=True)
    
    return {
        "loaded": len(loaded_agents),
        "agents": loaded_agents,
        "errors": errors,
    }


@router.get("/logs")
async def list_logs(session: AsyncSession = Depends(get_async_session)) -> dict:
    result = await session.execute(select(ExecutionLog))
    return {"logs": [log.id for log in result.scalars().all()]}
