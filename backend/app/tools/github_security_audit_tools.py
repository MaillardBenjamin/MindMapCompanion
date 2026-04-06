"""
Outil Agno : récupère le dernier commit d'une branche GitHub et les diffs pour audit de sécurité.
"""

import json
import logging
from typing import Optional

from agno.tools import Toolkit, tool

from app.core.config import get_settings
from app.services.github_last_commit import fetch_last_commit_audit_payload, format_payload_for_llm

logger = logging.getLogger(__name__)


class GitHubSecurityAuditTools(Toolkit):
    """
    Connexion lecture seule à l'API GitHub : dernier commit d'une branche + patches des fichiers.
    Jeton optionnel : variable d'environnement GITHUB_TOKEN (recommandé pour dépôts privés).
    """

    def __init__(self, github_token: Optional[str] = None, **kwargs):
        self._token_override = github_token
        super().__init__(
            name="github_security_audit_tools",
            tools=[self.fetch_last_commit_diff_for_security_audit],
            **kwargs,
        )

    def _token(self) -> str:
        if self._token_override is not None:
            return self._token_override
        return (get_settings().github_token or "").strip()

    @tool(
        description=(
            "Récupère le DERNIER commit sur une branche GitHub (owner, repo, branch) et les diffs des fichiers modifiés. "
            "À appeler avant d'écrire l'audit de sécurité. owner et repo sont obligatoires (ex: owner=microsoft, repo=vscode). "
            "branch par défaut : main. Pour un dépôt privé, le serveur doit avoir GITHUB_TOKEN configuré."
        )
    )
    def fetch_last_commit_diff_for_security_audit(
        self,
        owner: str,
        repo: str,
        branch: str = "main",
    ) -> str:
        """
        Lit le dernier commit sur la branche indiquée et retourne métadonnées + patches (JSON).

        Args:
            owner: Propriétaire du dépôt (utilisateur ou organisation).
            repo: Nom du dépôt.
            branch: Branche ou tag (défaut: main).

        Returns:
            JSON avec commit (sha, message, auteur, date, url) et liste files (filename, status, patch, …).
        """
        payload, err = fetch_last_commit_audit_payload(
            owner.strip(),
            repo.strip(),
            (branch or "main").strip(),
            token=self._token() or None,
        )
        if err:
            logger.info("[GitHubSecurityAuditTools] fetch erreur=%s owner=%s repo=%s branch=%s", err, owner, repo, branch)
        return format_payload_for_llm(payload)
