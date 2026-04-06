"""
Outils Agno : vérification HTTP + scénario Playwright généré par IA depuis des instructions en langage naturel ; alerte email si échec.
"""

import json
import logging
from typing import Any, Dict, Optional, Union

from agno.tools import Toolkit, tool

from app.services.site_health_check import run_site_health_check

logger = logging.getLogger(__name__)


class SiteHealthCheckTools(Toolkit):
    """
    Contrôle qu'une URL répond, traduit des instructions (FR/EN) en plan Playwright via le LLM,
    exécute le scénario ; envoie un email si le site est down (HTTP) ou si le scénario échoue.

    Configuration (frontmatter YAML de l'agent ou champs dédiés) :
    - alert_email : destinataire des alertes (obligatoire pour les notifications)
    - site_check_timeout_ms : timeout navigation/actions (défaut 30000)
    - site_check_headless : true/false (défaut true) — navigateur invisible ; mettre false pour voir Chromium localement
    Le paramètre d'outil show_browser sur une exécution donnée prime sur cette valeur.

    SMTP : mêmes variables que le reste de l'app (IMAP_HOST comme hôte SMTP, IMAP_USER, IMAP_PASSWORD).
    """

    def __init__(self, agent_config: Optional[Dict[str, Any]] = None, **kwargs):
        self.agent_config = agent_config or {}
        super().__init__(
            name="site_health_check_tools",
            tools=[self.verify_site_health],
            **kwargs,
        )

    def _timeout_ms(self) -> int:
        raw = self.agent_config.get("site_check_timeout_ms", 30_000)
        try:
            return max(5_000, int(raw))
        except (TypeError, ValueError):
            return 30_000

    def _headless(self) -> bool:
        h = self.agent_config.get("site_check_headless", True)
        if isinstance(h, str):
            return h.strip().lower() in ("true", "1", "yes", "oui")
        return bool(h)

    def _resolve_headless(self, show_browser: Union[str, bool, None]) -> bool:
        """
        Playwright : headless=True = pas de fenêtre. show_browser indique qu'on veut voir le navigateur.
        Valeurs : bool True = fenêtre visible ; False = forcer headless ; str "", "true", "false" (formulaire).
        """
        if show_browser is True:
            return False
        if show_browser is False:
            return True
        s = str(show_browser or "").strip().lower()
        if s in ("true", "1", "yes", "oui"):
            return False
        if s in ("false", "0", "no", "non"):
            return True
        return self._headless()

    def _http_timeout(self) -> float:
        raw = self.agent_config.get("site_check_http_timeout_sec", 15)
        try:
            return max(3.0, float(raw))
        except (TypeError, ValueError):
            return 15.0

    @tool(
        description=(
            "Vérifie qu'un site répond en HTTP puis exécute un scénario Playwright. "
            "Les « instructions » en langage naturel sont traduites en actions Playwright par le modèle. "
            "Si la page est injoignable (HTTP) ou si une étape échoue, un email est envoyé à alert_email_override "
            "ou à l'adresse configurée dans l'agent (alert_email). "
            "Paramètres : url (obligatoire), instructions (étapes à faire assertions FR/EN), "
            "alert_email_override (optionnel), steps_json (optionnel), "
            "show_browser (optionnel, true/false : true ouvre une fenêtre Chromium pour suivre le scénario — utile en local, "
            "sur un serveur sans écran laisser false ou défaut)."
        )
    )
    def verify_site_health(
        self,
        url: str,
        instructions: str = "",
        alert_email_override: str = "",
        steps_json: str = "",
        show_browser: Union[str, bool, None] = "",
    ) -> str:
        """
        Args:
            url: URL complète https://...
            instructions: Description des manipulations et vérifications (langage naturel).
            alert_email_override: Surclasse l'email configuré sur l'agent si non vide.
            steps_json: JSON tableau d'étapes (même schéma que le plan IA) pour désactiver la génération.
            show_browser: true/oui (str ou bool) → fenêtre visible ; false → headless ; vide/None → site_check_headless YAML.
        """
        url = (url or "").strip()
        alert = (alert_email_override or "").strip() or (self.agent_config.get("alert_email") or "").strip()
        headless = self._resolve_headless(show_browser)

        result = run_site_health_check(
            url,
            instructions or "",
            alert_email=alert,
            steps_json_override=(steps_json or "").strip() or None,
            default_timeout_ms=self._timeout_ms(),
            headless=headless,
            http_timeout_sec=self._http_timeout(),
        )
        logger.info(
            "[SiteHealthCheckTools] url=%s headless=%s http_ok=%s pw_ok=%s alert_sent=%s",
            url,
            headless,
            result.get("http_ok"),
            result.get("playwright_ok"),
            result.get("alert_sent"),
        )
        for line in result.get("playwright_logs") or []:
            logger.info("[SiteHealthCheckTools][PW] %s", line)
        return json.dumps(result, indent=2, ensure_ascii=False)
