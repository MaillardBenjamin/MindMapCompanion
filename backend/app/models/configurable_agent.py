from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ConfigurableAgent(Base):
    """Agent configurable via fichier .md avec prompt structuré, sortie, outils et serveurs MCP"""
    __tablename__ = "configurable_agents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Identification
    name = Column(String, nullable=False, index=True)
    slug = Column(String, unique=True, nullable=False, index=True)  # Identifiant unique pour l'API
    description = Column(Text, nullable=True)
    
    # Configuration (fichier .md parsé)
    markdown_config = Column(Text, nullable=False)  # Contenu du fichier .md
    prompt_template = Column(Text, nullable=False)  # Template de prompt avec {{input_text}}
    input_schema = Column(JSON, nullable=True)  # Schéma JSON pour les champs du formulaire
    output_schema = Column(JSON, nullable=True)  # Schéma JSON pour valider/parser la sortie
    tools = Column(JSON, nullable=True)  # Liste des outils disponibles (IDs)
    mcp_servers = Column(JSON, nullable=True)  # Liste des serveurs MCP (noms)
    
    # Persona/Instructions
    persona = Column(Text, nullable=True)  # Description du rôle/persona de l'agent
    instructions = Column(Text, nullable=True)  # Instructions additionnelles
    
    # Statut
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=False)  # Si True, accessible à tous les utilisateurs
    
    # Métadonnées
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relations
    user = relationship("User", back_populates="configurable_agents")
    execution_logs = relationship("AgentExecutionLog", back_populates="agent", cascade="all, delete-orphan")


class AgentExecutionLog(Base):
    """Journal des exécutions d'agents configurables"""
    __tablename__ = "agent_execution_logs"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("configurable_agents.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Données d'exécution
    input_text = Column(Text, nullable=False)  # Texte qui complète le prompt
    prompt_used = Column(Text, nullable=False)  # Prompt final utilisé
    output_raw = Column(Text, nullable=True)  # Sortie brute de l'agent
    output_parsed = Column(JSON, nullable=True)  # Sortie parsée selon le schéma
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    # Métadonnées
    execution_time_ms = Column(Integer, nullable=True)  # Temps d'exécution en ms
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    agent = relationship("ConfigurableAgent", back_populates="execution_logs")
    user = relationship("User")
