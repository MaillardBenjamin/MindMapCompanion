"""
Agents IA basés sur Agno avec OpenAI comme moteur.

Ce module contient les différents agents IA exposés via REST:
- MindmapOrganizer: Organise le texte dans le mindmap (thèmes, sous-thèmes, etc.)
- MindmapReorganizer: Réorganise la structure du mindmap existant
- TTSPreprocessorAgent: Prépare un texte pour la synthèse vocale (sans markdown prononcé)

Agents futurs prévus:
- CVMatcher: Matching offres d'emploi / CV
- EmailResponder: Automatisation de réponses aux mails
- ReminderCreator: Création de rappels intelligents
- ArticleWriter: Rédaction d'articles
"""

from app.agents.base import AgentBase
from app.agents.mindmap_organizer import MindmapOrganizerAgent
from app.agents.mindmap_reorganizer import MindmapReorganizerAgent
from app.agents.tts_preprocessor_agent import TTSPreprocessorAgent, tts_preprocessor_agent
from app.agents.github_security_audit import GitHubSecurityAuditAgent, github_security_audit_agent

__all__ = [
    "AgentBase",
    "MindmapOrganizerAgent",
    "MindmapReorganizerAgent",
    "TTSPreprocessorAgent",
    "tts_preprocessor_agent",
    "GitHubSecurityAuditAgent",
    "github_security_audit_agent",
]
