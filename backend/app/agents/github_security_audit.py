"""
Agent d'audit de sécurité sur le dernier commit d'un dépôt GitHub (branche configurable).
"""

import json
import logging
from typing import Any, Optional

from agno.agent import Agent

from app.agents.base import AgentBase, AgentResponse
from app.core.config import get_settings
from app.services.github_last_commit import fetch_last_commit_audit_payload, format_payload_for_llm
from app.tools.github_security_audit_tools import GitHubSecurityAuditTools

logger = logging.getLogger(__name__)


class GitHubSecurityAuditAgent(AgentBase):
    """Expert cybersécurité : analyse les changements du dernier commit GitHub."""

    @property
    def name(self) -> str:
        return "GitHubSecurityAudit"

    @property
    def description(self) -> str:
        return (
            "Se connecte à un dépôt GitHub, lit le dernier commit sur une branche donnée, "
            "et produit un audit de sécurité du code modifié (bonnes pratiques, risques, recommandations)."
        )

    def _create_agent(self) -> Agent:
        return Agent(
            name=self.name,
            model=self.model,
            tools=[GitHubSecurityAuditTools()],
            instructions="""Tu es un expert senior en cybersécurité applicative (AppSec) et révision de code sécurisé.

MISSION:
1. Utilise obligatoirement l'outil fetch_last_commit_diff_for_security_audit avec les paramètres fournis (owner, repo, branch).
2. Si l'outil retourne une erreur JSON, explique-la clairement et indique les actions correctives (token, nom du dépôt, branche).
3. Si des fichiers/patches sont présents, analyse-les pour un audit de sécurité du code **introduit ou modifié** dans ce commit.

CADRE D'ANALYSE (non exhaustif, adapte selon les langages détectés):
- Gestion des secrets (clés API, mots de passe, jetons dans le code ou les configs).
- Injections (SQL, commande, XSS, path traversal, désérialisation).
- Authentification, autorisation, contrôle d'accès, IDOR, élévation de privilèges.
- Cryptographie (algorithmes obsolètes, absence de TLS, stockage de mots de passe, IV/nonce, comparaisons sensibles au timing).
- Validation des entrées, limites, uploads, SSRF.
- Journalisation et fuite d'informations sensibles.
- Dépendances et surface d'attaque (si visibles dans le diff).
- Configuration et erreurs (messages d'erreur trop bavards, debug en production).

FORMAT DE RÉPONSE:
- Rédige en **français**, structuré en Markdown (##, ###, listes, tableaux si utile).
- Sections suggérées : Résumé exécutif, Périmètre (commit, branche, fichiers), Findings (sévérité : Critique / Élevée / Moyenne / Faible / Info), Recommandations priorisées, Références (OWASP, CWE si pertinent).
- Pour chaque finding : fichier concerné, nature du risque, scénario d'exploitation abstrait, remédiation concrète.
- Si le diff est tronqué ou absent pour certains fichiers, le signaler et recommander une revue manuelle sur GitHub.

Ne divulgue pas de contenu sensible extrait du code dans un ton alarmiste inutile ; reste factuel et professionnel.""",
        )

    async def execute(
        self,
        owner: str,
        repo: str,
        branch: str = "main",
        extra_context: Optional[str] = None,
        **kwargs: Any,
    ) -> AgentResponse:
        owner = (owner or "").strip()
        repo = (repo or "").strip()
        branch = (branch or "main").strip()
        if not owner or not repo:
            return AgentResponse(
                success=False,
                message="Paramètres manquants",
                error="owner et repo sont obligatoires.",
            )

        settings = get_settings()

        try:
            if getattr(settings, "skip_agent_llm", False):
                token = (settings.github_token or "").strip() or None
                payload, fetch_err = fetch_last_commit_audit_payload(owner, repo, branch, token=token)
                raw_json = format_payload_for_llm(payload)
                logger.info("[GitHubSecurityAudit] SKIP_AGENT_LLM : retour des données brutes uniquement")
                return AgentResponse(
                    success=True,
                    message="Données du dernier commit récupérées (audit LLM désactivé par SKIP_AGENT_LLM).",
                    data={
                        "owner": owner,
                        "repo": repo,
                        "branch": branch,
                        "fetch_error": fetch_err,
                        "raw_fetch": json.loads(raw_json) if raw_json else None,
                    },
                )

            extra = (extra_context or "").strip()
            prompt_parts = [
                f"Effectue l'audit de sécurité demandé pour le dépôt GitHub `{owner}/{repo}` sur la branche `{branch}`.",
                "Commence par appeler l'outil fetch_last_commit_diff_for_security_audit avec : "
                f"owner=\"{owner}\", repo=\"{repo}\", branch=\"{branch}\".",
            ]
            if extra:
                prompt_parts.append(f"Contexte ou consignes additionnelles du demandeur :\n{extra}")
            prompt = "\n\n".join(prompt_parts)

            response = await self.agent.arun(prompt)
            content = getattr(response, "content", None) or str(response)
            cleaned = (content or "").strip()
            if not cleaned:
                cleaned = "Aucune réponse du modèle."

            return AgentResponse(
                success=True,
                message="Audit de sécurité terminé",
                data={
                    "owner": owner,
                    "repo": repo,
                    "branch": branch,
                    "audit_markdown": cleaned,
                },
            )
        except Exception as e:
            logger.error("[GitHubSecurityAudit] Erreur: %s", e, exc_info=True)
            return AgentResponse(
                success=False,
                message="Échec de l'audit",
                error=str(e),
            )


github_security_audit_agent = GitHubSecurityAuditAgent()
