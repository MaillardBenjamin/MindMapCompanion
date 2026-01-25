"""
Classe de base pour tous les agents IA.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from app.core.config import get_settings


class AgentResponse(BaseModel):
    """Réponse standard d'un agent"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class AgentBase(ABC):
    """Classe de base pour tous les agents IA"""
    
    def __init__(self):
        self.settings = get_settings()
        self.model = self._create_model()
        self.agent = self._create_agent()
    
    def _create_model(self) -> OpenAIChat:
        """Crée le modèle OpenAI"""
        return OpenAIChat(
            id=self.settings.agno_model,
            api_key=self.settings.agno_api_key,
        )
    
    @abstractmethod
    def _create_agent(self) -> Agent:
        """Crée l'agent Agno - à implémenter par les sous-classes"""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> AgentResponse:
        """Exécute l'agent - à implémenter par les sous-classes"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Nom de l'agent"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Description de l'agent"""
        pass
