"""
Agents IA basés sur Agno avec OpenAI comme moteur.

Ce module contient les différents agents IA exposés via REST:
- MindmapOrganizer: Organise le texte dans le mindmap (thèmes, sous-thèmes, etc.)
- MindmapReorganizer: Réorganise la structure du mindmap existant

Agents futurs prévus:
- CVMatcher: Matching offres d'emploi / CV
- EmailResponder: Automatisation de réponses aux mails
- ReminderCreator: Création de rappels intelligents
- ArticleWriter: Rédaction d'articles
"""

from app.agents.base import AgentBase
from app.agents.mindmap_organizer import MindmapOrganizerAgent
from app.agents.mindmap_reorganizer import MindmapReorganizerAgent

__all__ = [
    "AgentBase",
    "MindmapOrganizerAgent",
    "MindmapReorganizerAgent",
]
