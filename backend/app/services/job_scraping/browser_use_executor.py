"""
Exécuteur Browser-Use pour les configurations de scraping.

Utilise browser-use avec Ollama pour exécuter les tâches de scraping
de manière intelligente via des instructions en langage naturel.
"""

import os
import asyncio
import logging
import json
import time
import re
from uuid import uuid4
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.services.job_scraping.scraper_config_parser import (
    ScraperConfig,
    TemplateResolver,
)
from app.services.job_scraping.storage_manager import JobOffer
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Flag pour n'appliquer le patch qu'une fois
_playwright_devtools_patch_applied = False


class _LaunchContextArgsWrapper:
    """
    Wrapper non-Pydantic autour de BrowserLaunchPersistentContextArgs.
    Expose model_dump() en retirant 'devtools' (non supporté par Playwright Python).
    On ne modifie jamais l'objet Pydantic, on retourne ce wrapper à la place.
    """

    def __init__(self, args: Any) -> None:
        self._args = args

    def model_dump(self, mode: str = "python", **kwargs: Any) -> Any:
        out = self._args.model_dump(mode=mode, **kwargs)
        if isinstance(out, dict):
            out = {k: v for k, v in out.items() if k != "devtools"}
        return out


def _apply_playwright_devtools_patch() -> None:
    """
    Retire le kwarg 'devtools' des kwargs passés à launch_persistent_context.
    L'API générée de Playwright (async_api) n'accepte pas ce paramètre.
    On patche BrowserProfile.kwargs_for_launch_persistent_context pour
    retourner un wrapper dont model_dump() exclut 'devtools' (sans toucher au modèle Pydantic).
    """
    global _playwright_devtools_patch_applied
    if _playwright_devtools_patch_applied:
        return
    try:
        from browser_use.browser.profile import (
            BrowserProfile,
            BrowserLaunchPersistentContextArgs,
        )

        _original_kwargs_for_launch = BrowserProfile.kwargs_for_launch_persistent_context

        def _patched_kwargs_for_launch_persistent_context(self: BrowserProfile) -> Any:  # type: ignore[no-untyped-def]
            args = _original_kwargs_for_launch(self)
            return _LaunchContextArgsWrapper(args)

        BrowserProfile.kwargs_for_launch_persistent_context = _patched_kwargs_for_launch_persistent_context  # type: ignore[assignment]
        _playwright_devtools_patch_applied = True
        logger.info(
            "[BrowserUseExecutor] Patch appliqué: suppression du kwarg devtools pour launch_persistent_context (compat Playwright Python)"
        )
    except Exception as e:
        logger.warning("[BrowserUseExecutor] Patch devtools non appliqué: %s", e)


class _OllamaLLMWrapper:
    """
    Wrapper autour de ChatOllama pour contourner l'erreur Pydantic:
    browser-use fait setattr(llm, 'ainvoke', ...) mais ChatOllama (Pydantic) refuse.
    Ce wrapper est un objet Python classique qui accepte les attributs dynamiques.
    """

    def __init__(self, llm):
        object.__setattr__(self, "_llm", llm)
        # browser-use utilise llm.provider pour ses logs/metrics
        # (ChatOllama n'expose pas forcément cet attribut).
        object.__setattr__(self, "provider", "ollama")
        # browser-use (cloud_events) accède à llm.model_name
        # ChatOllama expose généralement .model (str), mais pas .model_name.
        try:
            model = getattr(llm, "model", None) or getattr(llm, "model_name", None)
        except Exception:
            model = None
        object.__setattr__(self, "model_name", model or "unknown")

    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, "_llm"), name)

    def __setattr__(self, name, value):
        # Autoriser les attributs dynamiques (ex: ainvoke) que browser-use monkey-patche.
        object.__setattr__(self, name, value)


class BrowserUseExecutor:
    """
    Exécute les instructions de scraping en utilisant browser-use avec Ollama.
    
    Utilise l'IA pour comprendre et exécuter les tâches de scraping
    à partir d'instructions en langage naturel.
    """
    
    def __init__(self, config: ScraperConfig, context: Optional[Dict[str, Any]] = None):
        """
        Initialise l'exécuteur.
        
        Args:
            config: Configuration du scraper
            context: Contexte initial pour la résolution des templates
        """
        self.config = config
        self.context = context or {}
        self.template_resolver = TemplateResolver(self._build_initial_context())
        
        self.agent = None
        self.browser = None
        self.extracted_data: List[Dict[str, Any]] = []
        
        # Configuration Ollama
        self.settings = get_settings()
        # Debug/diag runtime (via variables d'environnement)
        self.debug_enabled = os.getenv("BROWSER_USE_DEBUG", "false").lower() in {"1", "true", "yes", "on"}
        self.debug_slow_seconds = self._parse_float_env("BROWSER_USE_DEBUG_SLOW_SECONDS", 1.5)
        self.force_ui_prep = os.getenv("BROWSER_USE_FORCE_UI_PREP", "true").lower() in {"1", "true", "yes", "on"}
        self._phase_start = time.monotonic()

    @staticmethod
    def _parse_float_env(name: str, default: float) -> float:
        """Parse une variable d'env float avec fallback sûr."""
        raw = os.getenv(name)
        if raw is None:
            return default
        try:
            value = float(raw)
            return value if value >= 0 else default
        except ValueError:
            return default

    @staticmethod
    def _truncate(value: Any, max_len: int = 800) -> str:
        """Représentation compacte pour les logs debug."""
        text = str(value)
        if len(text) <= max_len:
            return text
        return text[:max_len] + "... [truncated]"

    def _enable_browser_use_debug_logs(self) -> None:
        """Augmente le niveau de logs des composants browser-use en mode debug."""
        if not self.debug_enabled:
            return
        for logger_name in [
            "browser_use",
            "browser_use.agent",
            "browser_use.controller",
            "browser_use.browser",
        ]:
            logging.getLogger(logger_name).setLevel(logging.DEBUG)
        logger.info(
            "[BrowserUseExecutor][DEBUG] Logs browser_use en DEBUG activés | slow_seconds=%.2f",
            self.debug_slow_seconds,
        )

    def _log_phase(self, phase: str, extra: Optional[str] = None) -> None:
        """Trace de déroulement toujours active (niveau INFO)."""
        elapsed = time.monotonic() - self._phase_start
        suffix = f" | {extra}" if extra else ""
        logger.info("[BrowserUseExecutor][FLOW +%.2fs] %s%s", elapsed, phase, suffix)

    async def _debug_pause(self, reason: str) -> None:
        """Pause volontaire pour rendre l'exécution visible en mode debug."""
        if not self.debug_enabled:
            return
        logger.info(
            "[BrowserUseExecutor][DEBUG] Pause %.2fs: %s",
            self.debug_slow_seconds,
            reason,
        )
        await asyncio.sleep(self.debug_slow_seconds)

    def _log_agent_history_debug(self, result: Any) -> None:
        """Log détaillé du résultat AgentHistoryList pour diagnostiquer les erreurs actions/modèle."""
        if not self.debug_enabled:
            return
        try:
            all_results = getattr(result, "all_results", None)
            if isinstance(all_results, list):
                logger.info("[BrowserUseExecutor][DEBUG] all_results count=%d", len(all_results))
                for i, action_result in enumerate(all_results, start=1):
                    logger.info(
                        "[BrowserUseExecutor][DEBUG] action_result[%d]: is_done=%s success=%s error=%s extracted_content=%s",
                        i,
                        getattr(action_result, "is_done", None),
                        getattr(action_result, "success", None),
                        self._truncate(getattr(action_result, "error", None), 400),
                        self._truncate(getattr(action_result, "extracted_content", None), 400),
                    )
            else:
                logger.info(
                    "[BrowserUseExecutor][DEBUG] Pas de all_results list, type(result)=%s",
                    type(result).__name__,
                )

            all_model_outputs = getattr(result, "all_model_outputs", None)
            if isinstance(all_model_outputs, list):
                logger.info("[BrowserUseExecutor][DEBUG] all_model_outputs count=%d", len(all_model_outputs))
                for i, model_out in enumerate(all_model_outputs, start=1):
                    logger.info(
                        "[BrowserUseExecutor][DEBUG] model_output[%d]=%s",
                        i,
                        self._truncate(model_out, 1000),
                    )
        except Exception as e:
            logger.warning("[BrowserUseExecutor][DEBUG] Impossible de logger l'historique agent: %s", e)

    def _log_agent_history_info(self, result: Any) -> None:
        """Résumé INFO toujours actif du résultat Browser-Use."""
        try:
            all_results = getattr(result, "all_results", None)
            all_model_outputs = getattr(result, "all_model_outputs", None)
            count_results = len(all_results) if isinstance(all_results, list) else 0
            count_model = len(all_model_outputs) if isinstance(all_model_outputs, list) else 0
            self._log_phase(
                "AgentHistory reçu",
                f"all_results={count_results}, all_model_outputs={count_model}",
            )
            if isinstance(all_results, list):
                for i, action_result in enumerate(all_results, start=1):
                    logger.info(
                        "[BrowserUseExecutor][FLOW] ActionResult[%d] is_done=%s success=%s error=%s",
                        i,
                        getattr(action_result, "is_done", None),
                        getattr(action_result, "success", None),
                        self._truncate(getattr(action_result, "error", None), 300),
                    )
            if isinstance(all_model_outputs, list) and all_model_outputs:
                logger.info(
                    "[BrowserUseExecutor][FLOW] Premier model_output=%s",
                    self._truncate(all_model_outputs[0], 700),
                )
            elif isinstance(all_model_outputs, list):
                logger.info("[BrowserUseExecutor][FLOW] Aucun model_output produit par le LLM")
        except Exception as e:
            logger.warning("[BrowserUseExecutor][FLOW] Impossible de résumer AgentHistory: %s", e)

    def _dump_run_diagnostics(
        self,
        *,
        instructions: str,
        start_url: str,
        search_params: Optional[Dict[str, Any]],
        initial_actions: List[Dict[str, Any]],
        result: Any,
    ) -> None:
        """Sauvegarde un dump exploitable du run pour diagnostic hors console."""
        try:
            runs_dir = Path(__file__).resolve().parents[3] / "data" / "logs" / "browser_use_runs"
            runs_dir.mkdir(parents=True, exist_ok=True)
            run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8]
            dump_path = runs_dir / f"run-{run_id}.json"

            all_results = getattr(result, "all_results", None)
            all_model_outputs = getattr(result, "all_model_outputs", None)

            payload = {
                "run_id": run_id,
                "created_at": datetime.now().isoformat(),
                "scraper_name": self.config.name,
                "start_url": start_url,
                "search_params": search_params or {},
                "initial_actions": initial_actions,
                "instructions": instructions,
                "result_type": type(result).__name__,
                "all_results": (
                    [r.model_dump() if hasattr(r, "model_dump") else str(r) for r in all_results]
                    if isinstance(all_results, list)
                    else all_results
                ),
                "all_model_outputs": (
                    [m.model_dump() if hasattr(m, "model_dump") else str(m) for m in all_model_outputs]
                    if isinstance(all_model_outputs, list)
                    else all_model_outputs
                ),
            }
            dump_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info("[BrowserUseExecutor][FLOW] Diagnostic run dump: %s", dump_path)
        except Exception as e:
            logger.warning("[BrowserUseExecutor][FLOW] Impossible d'écrire le dump de diagnostic: %s", e)

    async def _force_click_by_text(self, page: Any, patterns: List[str], label: str) -> bool:
        """Clic robuste par texte (document puis iframes) avec logs INFO."""
        regex = re.compile("|".join(patterns), re.IGNORECASE)
        # 1) Document principal
        try:
            loc = page.get_by_role("button", name=regex).first
            await loc.click(timeout=3000)
            logger.info("[BrowserUseExecutor][FORCE] Clic %s réussi dans le document principal", label)
            return True
        except Exception:
            pass
        try:
            loc = page.get_by_text(regex).first
            await loc.click(timeout=3000)
            logger.info("[BrowserUseExecutor][FORCE] Clic %s (by_text) réussi dans le document principal", label)
            return True
        except Exception:
            pass

        # 2) Iframes
        frames = page.frames
        for idx, frame in enumerate(frames):
            try:
                loc = frame.get_by_role("button", name=regex).first
                await loc.click(timeout=2000)
                logger.info("[BrowserUseExecutor][FORCE] Clic %s réussi dans iframe[%d]", label, idx)
                return True
            except Exception:
                pass
            try:
                loc = frame.get_by_text(regex).first
                await loc.click(timeout=2000)
                logger.info("[BrowserUseExecutor][FORCE] Clic %s (by_text) réussi dans iframe[%d]", label, idx)
                return True
            except Exception:
                pass
        logger.info("[BrowserUseExecutor][FORCE] Clic %s non trouvé", label)
        return False

    async def _run_forced_ui_prep(self, start_url: str) -> None:
        """
        Prépare l'UI de façon déterministe (cookies + rechercher) avant Browser-Use.
        Ouvre un navigateur Playwright séparé pour visibilité/diagnostic.
        """
        if not self.force_ui_prep:
            self._log_phase("Pré-run UI forcé désactivé")
            return
        self._log_phase("Pré-run UI forcé démarré")
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.config.browser.headless)
                context = await browser.new_context(
                    viewport=self.config.browser.viewport or {"width": 1920, "height": 1080}
                )
                page = await context.new_page()
                await page.goto(start_url, wait_until="domcontentloaded", timeout=max(self.config.browser.navigation_timeout, 30000))
                logger.info("[BrowserUseExecutor][FORCE] Page ouverte: %s", start_url)
                await page.wait_for_timeout(1200)

                # Cookies (TOUT ACCEPTER variants)
                await self._force_click_by_text(
                    page,
                    patterns=[r"TOUT\\s+ACCEPTER", r"Tout\\s+accepter", r"Accepter", r"J['’ ]accepte"],
                    label="cookies",
                )
                await page.wait_for_timeout(1000)

                # Bouton rechercher
                await self._force_click_by_text(
                    page,
                    patterns=[r"Rechercher", r"Lancer\\s+la\\s+recherche"],
                    label="rechercher",
                )
                await page.wait_for_timeout(1800)
                logger.info("[BrowserUseExecutor][FORCE] Pré-run UI forcé terminé")
                await context.close()
                await browser.close()
        except Exception as e:
            logger.warning("[BrowserUseExecutor][FORCE] Pré-run UI forcé en échec (non bloquant): %s", e)
        
    def _build_initial_context(self) -> Dict[str, Any]:
        """Construit le contexte initial pour les templates"""
        context = {
            "site_url": self.config.site_url,
            "timestamp": datetime.now().isoformat(),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "extracted_offers": [],
        }
        
        # Ajouter les credentials depuis les variables d'environnement
        credentials = {}
        if self.config.credentials.email_env:
            credentials["email"] = os.environ.get(self.config.credentials.email_env, "")
        if self.config.credentials.password_env:
            credentials["password"] = os.environ.get(self.config.credentials.password_env, "")
        context["credentials"] = credentials
        
        # Ajouter le contexte fourni
        context.update(self.context)
        
        return context
    
    async def execute(self, search_params: Optional[Dict[str, Any]] = None) -> List[JobOffer]:
        """
        Exécute le scraping selon la configuration.
        
        Args:
            search_params: Paramètres de recherche (keywords, location, etc.)
        
        Returns:
            Liste des offres extraites
        """
        if search_params:
            self.template_resolver.add_to_context("search", search_params)
        self._phase_start = time.monotonic()
        self._log_phase("Début execute()", f"debug_enabled={self.debug_enabled}")
        
        try:
            # Par défaut, on évite le cloud sync/telemetry (peut générer des appels HTTP et du bruit 401)
            # L'utilisateur peut toujours réactiver via variables d'environnement.
            os.environ.setdefault("BROWSER_USE_CLOUD_SYNC", "false")
            os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")
            # Isoler les profils browser-use du ~/.config pour éviter les conflits de versions Playwright/Chromium.
            # (browser-use utilise un profil persistant par défaut)
            os.environ.setdefault(
                "BROWSER_USE_CONFIG_DIR",
                str((Path(__file__).resolve().parents[4] / ".browseruse").resolve()),
            )

            from browser_use import Agent
            from langchain_ollama import ChatOllama
            self._log_phase("Imports browser_use/langchain_ollama OK")
        except ImportError as e:
            logger.error("[BrowserUseExecutor] browser-use ou langchain-ollama n'est pas installé. Exécutez: pip install browser-use langchain-ollama")
            logger.error(f"[BrowserUseExecutor] Détails: {e}")
            return []
        
        logger.info(f"[BrowserUseExecutor] Démarrage du scraping pour {self.config.name}")
        
        try:
            self._enable_browser_use_debug_logs()
            self._log_phase("Préparation runtime Browser-Use")
            # Workaround compat Playwright Python:
            # browser-use passe `devtools` à launch_persistent_context(), mais Playwright Python ne supporte pas ce kwarg.
            # On monkey-patche launch_persistent_context pour retirer 'devtools' des kwargs avant l'appel.
            _apply_playwright_devtools_patch()
            self._log_phase("Patch Playwright appliqué (ou déjà actif)")

            # Configurer le modèle Ollama
            ollama_base_url = self.settings.ollama_base_url.strip().rstrip("/")
            # browser-use/langchain attend généralement l'URL racine (sans /v1)
            if ollama_base_url.endswith("/v1"):
                ollama_base_url = ollama_base_url[: -len("/v1")]
            
            logger.info(f"[BrowserUseExecutor] Configuration Ollama: {ollama_base_url} | Modèle: {self.settings.agno_model}")
            self._log_phase("Configuration LLM prête", f"base_url={ollama_base_url}, model={self.settings.agno_model}")
            
            chat_ollama = ChatOllama(
                model=self.settings.agno_model,
                base_url=ollama_base_url,
                temperature=0.1,  # Plus déterministe pour le scraping
            )
            
            # Wrapper pour contourner l'erreur Pydantic: ChatOllama refuse setattr('ainvoke').
            # browser-use appelle register_llm() qui fait setattr(llm, 'ainvoke', ...).
            llm = _OllamaLLMWrapper(chat_ollama)
            self._log_phase("Wrapper LLM construit")
            
            # Construire les instructions et l'URL de départ
            instructions = self._build_instructions(search_params)
            start_url = self._build_start_url(search_params)
            
            logger.info(f"[BrowserUseExecutor] Instructions générées: {len(instructions)} caractères")
            logger.info(f"[BrowserUseExecutor] URL de départ: {start_url}")
            self._log_phase("Tâche construite", f"instructions_len={len(instructions)}")
            logger.info("[BrowserUseExecutor][PROMPT] BEGIN_INSTRUCTIONS")
            logger.info("%s", instructions)
            for i, line in enumerate(instructions.splitlines(), start=1):
                logger.info("[BrowserUseExecutor][PROMPT][%03d] %s", i, line)
            logger.info("[BrowserUseExecutor][PROMPT] END_INSTRUCTIONS")
            logger.debug(f"[BrowserUseExecutor] Instructions:\n{instructions[:500]}...")
            if self.debug_enabled:
                logger.info(
                    "[BrowserUseExecutor][DEBUG] search_params=%s | existing_offer_ids=%d",
                    self._truncate(search_params, 1000),
                    len(self.context.get("existing_offer_ids", [])),
                )
            
            # Navigation initiale obligatoire : évite de rester sur about:blank et l'erreur "items"
            # (l'agent doit avoir au moins une action à faire ; sur about:blank le LLM peut renvoyer une structure invalide)
            initial_actions = [{"go_to_url": {"url": start_url, "new_tab": False}}]
            self._log_phase("Initial actions prêtes", self._truncate(initial_actions, 300))

            # Préparation visuelle/déterministe de l'UI pour observer explicitement les clics.
            await self._run_forced_ui_prep(start_url)
            
            # Créer l'agent avec la tâche et la première action (aller sur le site)
            self.agent = Agent(
                task=instructions,
                llm=llm,
                use_vision=False,  # Désactiver la vision pour plus de rapidité
                initial_actions=initial_actions,
                validate_output=False,  # Éviter les échecs stricts sur le schéma de sortie du LLM
            )
            self._log_phase("Agent Browser-Use créé")

            await self._debug_pause("avant agent.run()")
            self._log_phase("Lancement agent.run()")
            
            result = await self.agent.run()
            self._log_phase("agent.run() terminé")
            await self._debug_pause("après agent.run(), avant parsing")
            
            logger.info(f"[BrowserUseExecutor] Tâche terminée. Résultat: {result}")
            self._log_agent_history_info(result)
            self._log_agent_history_debug(result)
            self._dump_run_diagnostics(
                instructions=instructions,
                start_url=start_url,
                search_params=search_params,
                initial_actions=initial_actions,
                result=result,
            )
            
            # Extraire les données du résultat
            self._log_phase("Début parsing résultat")
            self.extracted_data = self._parse_result(result)
            self._log_phase("Parsing terminé", f"extracted_data={len(self.extracted_data)}")
            
            # Convertir en JobOffers
            self._log_phase("Conversion en JobOffer")
            offers = self._convert_to_job_offers()
            self._log_phase("Conversion terminée", f"offers={len(offers)}")
            logger.info(f"[BrowserUseExecutor] Scraping terminé: {len(offers)} offres extraites")
            
            return offers
            
        except Exception as e:
            logger.error(f"[BrowserUseExecutor] Erreur lors du scraping: {e}", exc_info=True)
            return []
    
    def _build_start_url(self, search_params: Optional[Dict[str, Any]] = None) -> str:
        """Construit l'URL de départ avec les paramètres de recherche (comme le scraper Playwright Cadre Emploi)."""
        from urllib.parse import urlencode, unquote_plus
        base = self.config.site_url.rstrip("/")
        if not search_params:
            return base
        # Paramètres utilisés par Cadre Emploi
        motscles = search_params.get("motscles") or search_params.get("keywords") or ""
        if isinstance(motscles, str) and motscles:
            # Évite le double encodage (ex: DRH%252C) si les mots-clés arrivent déjà URL-encodés.
            motscles = unquote_plus(motscles).strip()
        reg = search_params.get("reg", "")
        tyc = search_params.get("tyc", "")
        salary_min = search_params.get("salary_min") or search_params.get("salary") or ""
        params = {"motscles": motscles, "reg": reg, "tyc": tyc, "salary": str(salary_min)}
        params = {k: v for k, v in params.items() if v is not None and str(v).strip() != ""}
        if not params:
            return base
        return f"{base}?{urlencode(params)}"

    def _build_instructions(self, search_params: Optional[Dict[str, Any]] = None) -> str:
        """
        Construit les instructions en langage naturel pour l'agent.
        
        Convertit la configuration du scraper en instructions compréhensibles
        par l'IA.
        """
        instructions = []
        
        # En-tête
        instructions.append(f"Tu es un assistant de scraping web spécialisé dans l'extraction d'offres d'emploi.")
        instructions.append(f"Tu dois extraire des offres d'emploi depuis {self.config.site_url}")
        instructions.append("")
        
        # Paramètres de recherche
        if search_params:
            instructions.append("Paramètres de recherche:")
            if "keywords" in search_params:
                instructions.append(f"- Mots-clés: {search_params['keywords']}")
            if "location" in search_params:
                instructions.append(f"- Localisation: {search_params['location']}")
            instructions.append("")
        
        # Instructions basées sur les étapes de configuration
        if hasattr(self.config, 'natural_language_instructions'):
            # Si des instructions en langage naturel sont fournies
            instructions.append("Tâches à effectuer:")
            instructions.append(self.config.natural_language_instructions)
        else:
            # Sinon, générer des instructions à partir des étapes Playwright
            instructions.append("Tâches à effectuer:")
            instructions.append("1. Navigue vers le site web")
            instructions.append("2. Recherche les offres d'emploi correspondant aux critères")
            instructions.append("3. Pour chaque offre, extraie les informations suivantes:")
            instructions.append("   - Titre du poste")
            instructions.append("   - Entreprise")
            instructions.append("   - Localisation")
            instructions.append("   - URL de l'offre")
            instructions.append("   - Description (si disponible)")
            instructions.append("   - Salaire (si disponible)")
            instructions.append("   - Type de contrat (CDI, CDD, etc.)")
            instructions.append("   - Date de publication (si disponible)")
        
        instructions.append("")
        instructions.append("Contraintes de navigation (obligatoires):")
        instructions.append("1. Si un bouton cookies 'TOUT ACCEPTER' apparaît (même dans un iframe), clique dessus avant toute extraction.")
        instructions.append("2. Clique ensuite sur le bouton 'Rechercher'.")
        instructions.append("3. N'arrête pas la tâche tant que la liste d'offres n'est pas visible.")
        instructions.append("4. N'affiche le JSON final qu'à la toute fin, après ces actions.")
        if self.debug_enabled:
            instructions.append("5. Mode debug: attends ~2 secondes après chaque navigation et clic important pour rendre les actions visibles.")
        instructions.append("")
        instructions.append("Format de sortie attendu:")
        instructions.append("Retourne un objet JSON avec une liste 'offers' contenant les offres extraites.")
        instructions.append("Chaque offre doit être un objet avec les champs: title, company, location, url, description, salary, contract_type, publish_date")
        
        # Filtrage des offres existantes
        if self.context.get("existing_offer_ids"):
            instructions.append("")
            instructions.append(f"IMPORTANT: Ignore les offres avec les IDs suivants (déjà scrapées): {len(self.context['existing_offer_ids'])} offres à ignorer")
        
        return "\n".join(instructions)
    
    def _parse_result(self, result: Any) -> List[Dict[str, Any]]:
        """
        Parse le résultat de l'agent pour extraire les données structurées.
        
        Args:
            result: Résultat retourné par browser-use
        
        Returns:
            Liste de dictionnaires avec les données extraites
        """
        extracted = []

        def _extract_from_payload(payload: Any) -> List[Dict[str, Any]]:
            """Extrait une liste d'offres depuis différentes formes de payload Browser-Use."""
            out: List[Dict[str, Any]] = []
            if payload is None:
                return out

            if isinstance(payload, str):
                # Essayer JSON direct
                try:
                    parsed = json.loads(payload)
                    return _extract_from_payload(parsed)
                except json.JSONDecodeError:
                    # Essayer d'extraire le premier objet JSON dans le texte
                    import re
                    matches = re.findall(r"\{.*\}", payload, re.DOTALL)
                    for match in matches:
                        try:
                            parsed = json.loads(match)
                            out.extend(_extract_from_payload(parsed))
                        except Exception:
                            continue
                    return out

            if isinstance(payload, dict):
                if isinstance(payload.get("offers"), list):
                    return [x for x in payload["offers"] if isinstance(x, dict)]
                if isinstance(payload.get("data"), list):
                    return [x for x in payload["data"] if isinstance(x, dict)]
                return out

            if isinstance(payload, list):
                return [x for x in payload if isinstance(x, dict)]

            # Objets Browser-Use (AgentHistoryList/ActionResult/Model objets)
            try:
                final_result = getattr(payload, "final_result", None)
                if callable(final_result):
                    out.extend(_extract_from_payload(final_result()))
                    if out:
                        return out
            except Exception:
                pass

            try:
                model_dump = getattr(payload, "model_dump", None)
                if callable(model_dump):
                    dumped = model_dump()
                    out.extend(_extract_from_payload(dumped))
                    if out:
                        return out
            except Exception:
                pass

            return out
        
        try:
            extracted = _extract_from_payload(result)
            
            logger.info(f"[BrowserUseExecutor] {len(extracted)} offres parsées depuis le résultat")
            
        except Exception as e:
            logger.error(f"[BrowserUseExecutor] Erreur lors du parsing du résultat: {e}")
        
        return extracted
    
    def _convert_to_job_offers(self) -> List[JobOffer]:
        """Convertit les données extraites en objets JobOffer"""
        offers = []
        
        for i, data in enumerate(self.extracted_data):
            try:
                offer = JobOffer(
                    id=data.get("id") or data.get("source_id") or data.get("offer_id") or f"{self.config.name}-{i}",
                    title=data.get("title", "Sans titre"),
                    company=data.get("company", "Entreprise inconnue"),
                    location=data.get("location", "Non spécifié"),
                    url=data.get("url", ""),
                    source=data.get("source", self.config.name),
                    description=data.get("description", data.get("full_description", "")),
                    salary=data.get("salary"),
                    contract_type=data.get("contract_type"),
                    publish_date=data.get("publish_date"),
                    requirements=data.get("requirements", []),
                    metadata=data,
                )
                offers.append(offer)
            except Exception as e:
                logger.warning(f"[BrowserUseExecutor] Erreur conversion offre {i}: {e}")
        
        return offers
