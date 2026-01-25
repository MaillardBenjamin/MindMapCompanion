from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any


# Schemas pour ConfigurableAgent
class ConfigurableAgentBase(BaseModel):
    name: str
    slug: str = Field(..., description="Identifiant unique pour l'API (format: slug-case)")
    description: Optional[str] = None
    markdown_config: str = Field(..., description="Contenu du fichier .md de configuration")
    prompt_template: str = Field(..., description="Template de prompt avec {{input_text}}")
    input_schema: Optional[Dict[str, Any]] = Field(default=None, description="Schéma JSON pour les champs du formulaire")
    output_schema: Optional[Dict[str, Any]] = None
    tools: Optional[List[str]] = None
    mcp_servers: Optional[List[str]] = None
    persona: Optional[str] = None
    instructions: Optional[str] = None
    is_active: bool = True
    is_public: bool = False


class ConfigurableAgentCreate(ConfigurableAgentBase):
    pass


class ConfigurableAgentUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    markdown_config: Optional[str] = None
    prompt_template: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    tools: Optional[List[str]] = None
    mcp_servers: Optional[List[str]] = None
    persona: Optional[str] = None
    instructions: Optional[str] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None


class ConfigurableAgentOut(ConfigurableAgentBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConfigurableAgentListOut(BaseModel):
    agents: List[ConfigurableAgentOut]


# Schemas pour l'exécution d'agents
class AgentExecuteRequest(BaseModel):
    input_text: str = Field(..., description="Texte qui complète le prompt et spécialise la demande")
    options: Optional[Dict[str, Any]] = Field(default=None, description="Options additionnelles pour l'exécution")


class AgentExecuteResponse(BaseModel):
    success: bool
    agent_id: int
    agent_name: str
    input_text: str
    prompt_used: str
    output_raw: Optional[str] = None
    output_parsed: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None
    created_at: datetime


# Schemas pour les logs d'exécution
class AgentExecutionLogOut(BaseModel):
    id: int
    agent_id: int
    agent_name: str
    user_id: int
    input_text: str
    prompt_used: str
    output_raw: Optional[str] = None
    output_parsed: Optional[Dict[str, Any]] = None
    success: bool
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AgentExecutionLogListOut(BaseModel):
    logs: List[AgentExecutionLogOut]
