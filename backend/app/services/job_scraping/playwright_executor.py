"""
Exécuteur Playwright pour les configurations de scraping.

Exécute les étapes définies dans les fichiers de configuration markdown
en utilisant l'API Playwright Python.
"""

import os
import re
import random
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin, urlparse, parse_qs

from app.services.job_scraping.scraper_config_parser import (
    ScraperConfig,
    PlaywrightStep,
    TemplateResolver,
)
from app.services.job_scraping.storage_manager import JobOffer

logger = logging.getLogger(__name__)


class PlaywrightExecutor:
    """
    Exécute les instructions Playwright depuis une configuration.
    
    Supporte toutes les actions Playwright courantes :
    - Navigation : goto, go_back, reload
    - Interactions : click, fill, select_option, check, hover, press, type
    - Attentes : wait, wait_for
    - Extraction : extract, extract_list
    - Contrôle de flux : for_each, if/else, retry, break
    - Utilitaires : screenshot, log, evaluate, scroll
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
        
        self.browser = None
        self.page = None
        self.extracted_data: List[Dict[str, Any]] = []
        
        # Anti-bot settings
        self.anti_bot = config.anti_bot or {}
        self.rate_limiting = config.rate_limiting or {}
        
        # État d'exécution
        self._should_break = False
    
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
        
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error("[PlaywrightExecutor] Playwright n'est pas installé. Exécutez: pip install playwright && playwright install chromium")
            return []
        
        logger.info(f"[PlaywrightExecutor] Démarrage du scraping pour {self.config.name}")
        
        async with async_playwright() as p:
            # Lancer le navigateur
            browser_options = {
                "headless": self.config.browser.headless,
            }
            
            self.browser = await p.chromium.launch(**browser_options)
            
            # Créer le contexte
            context_options = {
                "viewport": self.config.browser.viewport,
            }
            if self.config.browser.user_agent:
                context_options["user_agent"] = self.config.browser.user_agent
            
            browser_context = await self.browser.new_context(**context_options)
            browser_context.set_default_timeout(self.config.browser.timeout)
            browser_context.set_default_navigation_timeout(self.config.browser.navigation_timeout)
            
            self.page = await browser_context.new_page()
            
            try:
                # Exécuter toutes les étapes
                for i, step in enumerate(self.config.steps):
                    if self._should_break:
                        logger.info(f"[PlaywrightExecutor] Arrêt demandé après étape {i}")
                        break
                    
                    logger.debug(f"[PlaywrightExecutor] Exécution étape {i+1}/{len(self.config.steps)}: {step.action}")
                    
                    try:
                        await self._execute_step(step, step_index=i + 1, step_total=len(self.config.steps))
                        await self._apply_delays()
                    except Exception as e:
                        if step.on_error:
                            logger.warning(f"[PlaywrightExecutor] Erreur étape {i+1}, exécution on_error: {e}")
                            await self._handle_error(step.on_error, e)
                        else:
                            raise
                
                # Convertir les données extraites en JobOffers
                offers = self._convert_to_job_offers()
                logger.info(f"[PlaywrightExecutor] Scraping terminé: {len(offers)} offres extraites")
                return offers
                
            finally:
                await browser_context.close()
                await self.browser.close()
    
    def _format_step_log(self, action: str, params: Dict[str, Any]) -> str:
        """Format action + params pour les logs (code Playwright exécuté)."""
        def trunc(s: str, max_len: int = 200) -> str:
            s = str(s).strip()
            return (s[:max_len] + "...") if len(s) > max_len else s

        parts = [f"action={action}"]
        if action == "goto":
            parts.append(f"url={params.get('url', '')!r}")
        elif action == "click":
            if params.get("role") and params.get("name") is not None:
                parts.append(f"role={params['role']!r} name={params.get('name')!r}")
            else:
                parts.append(f"selector={params.get('selector', '')!r}")
            if params.get("options"):
                parts.append(f"options={params['options']}")
        elif action == "click_in_iframe":
            parts.append(f"iframe={params.get('iframe_selector', '')!r}")
            if params.get("role") and params.get("name") is not None:
                parts.append(f"role={params['role']!r} name={params.get('name')!r}")
            else:
                parts.append(f"selector={params.get('selector', '')!r}")
        elif action == "click_filter_text":
            parts.append(f"selector={params.get('selector', 'div')!r}")
            parts.append(f"text={params.get('text', '')!r}")
            parts.append(f"nth={params.get('nth', 0)}")
        elif action == "fill":
            if params.get("role") and params.get("name") is not None:
                parts.append(f"role={params['role']!r} name={params.get('name')!r}")
            else:
                parts.append(f"selector={params.get('selector', '')!r}")
            v = params.get("value", "")
            parts.append(f"value={trunc(v, 120)!r}")
        elif action == "select_option":
            parts.append(f"selector={params.get('selector', '')!r}")
            parts.append(f"value={params.get('value')!r}")
        elif action == "evaluate":
            code = params.get("code", "") or ""
            code_preview = trunc(code, 500).replace("\n", " \\n ")
            parts.append(f"code_len={len(code)}")
            parts.append(f"code={code_preview!r}")
        elif action == "wait":
            parts.append(f"timeout={params.get('timeout', 1000)}ms")
        elif action == "scroll":
            parts.append(f"direction={params.get('direction', 'down')}")
            if params.get("amount") is not None:
                parts.append(f"amount={params['amount']}")
            if params.get("selector"):
                parts.append(f"selector={params['selector']!r}")
        elif action == "handle_popup":
            parts.append(f"type={params.get('type', '')!r}")
            parts.append(f"selector={params.get('selector', '')!r}")
            parts.append(f"strategy={params.get('strategy', '')!r}")
        elif action == "extract_list":
            parts.append(f"container={params.get('container_selector', '')!r}")
            parts.append(f"item={params.get('item_selector', '')!r}")
        elif action == "extract":
            parts.append(f"fields={list(f.get('name') for f in (params.get('fields') or []))}")
        elif action == "wait_for":
            w = params
            if "selector" in w:
                parts.append(f"selector={w.get('selector')!r} state={w.get('state', 'visible')}")
            elif "url" in w:
                parts.append(f"url={w.get('url')!r}")
            elif "function" in w:
                parts.append("function=...")
        elif action == "check":
            if params.get("role") and params.get("name") is not None:
                parts.append(f"role={params['role']!r} name={params.get('name')!r}")
            else:
                parts.append(f"selector={params.get('selector', '')!r}")
        elif action == "paginate":
            parts.append(f"strategy={params.get('strategy', '')!r}")
            n = params.get("next_button", {})
            if isinstance(n, dict) and n.get("selector"):
                parts.append(f"next={n['selector']!r}")
        else:
            # Générique : paramètres principaux (exclure wait_for, on_error)
            for k, v in params.items():
                if k in ("wait_for", "on_error", "options") or v is None:
                    continue
                if isinstance(v, str) and len(v) > 150:
                    v = trunc(v, 150)
                try:
                    parts.append(f"{k}={v!r}")
                except Exception:
                    parts.append(f"{k}=...")

        return " ".join(parts)

    def _get_locator(self, params: Dict[str, Any], *, page_or_frame=None):
        """Retourne un locator Playwright : get_by_role(role, name) si fournis, sinon locator(selector)."""
        target = page_or_frame or self.page
        role, name = params.get("role"), params.get("name")
        if role and name is not None:
            return target.get_by_role(role, name=str(name))
        sel = params.get("selector")
        if not sel:
            raise ValueError("selector ou (role + name) requis")
        return target.locator(sel)

    async def _execute_step(self, step: PlaywrightStep, step_index: Optional[int] = None, step_total: Optional[int] = None):
        """Exécute une étape Playwright"""
        # Condition optionnelle : skip si key absente ou falsy
        if getattr(step, "condition", None) and isinstance(step.condition, dict):
            key = step.condition.get("key")
            if key:
                val = self.template_resolver.get(key)
                if not val:
                    logger.debug(f"[PlaywrightExecutor] Étape ignorée (condition key={key} falsy)")
                    return
        # Pour for_each, ne pas résoudre "steps" ici : ils seront résolus à l'exécution avec item en contexte
        if step.action == "for_each":
            params = {}
            for k, v in step.params.items():
                if k == "steps":
                    params[k] = v  # Laisser brut
                else:
                    params[k] = self.template_resolver.resolve(v)
        else:
            params = self.template_resolver.resolve(step.params)
        
        prefix = f"Étape {step_index}/{step_total} " if step_index is not None and step_total is not None else ""
        logger.info("[PlaywrightExecutor] ▶ %s%s", prefix, self._format_step_log(step.action, params))

        # Dispatch selon l'action
        action_method = getattr(self, f"_action_{step.action}", None)
        if action_method:
            result = await action_method(params)
            
            # Gérer le wait_for après l'action
            if step.wait_for:
                await self._execute_wait_for(step.wait_for)
            
            return result
        else:
            logger.warning(f"[PlaywrightExecutor] Action non supportée: {step.action}")
    
    async def _apply_delays(self):
        """Applique les délais anti-bot et rate limiting"""
        if self.anti_bot.get("enabled") and self.anti_bot.get("random_delays", {}).get("between_actions"):
            min_delay = self.anti_bot["random_delays"].get("min", 1000)
            max_delay = self.anti_bot["random_delays"].get("max", 3000)
            delay = random.randint(min_delay, max_delay)
            await asyncio.sleep(delay / 1000)
        
        if self.rate_limiting.get("enabled"):
            delay = self.rate_limiting.get("delay_between_requests", 1000)
            await asyncio.sleep(delay / 1000)
    
    async def _handle_error(self, error_handlers: List[Dict[str, Any]], error: Exception):
        """Gère les erreurs selon la configuration on_error"""
        for handler in error_handlers:
            action = handler.get("action")
            if action == "wait":
                await asyncio.sleep(handler.get("timeout", 1000) / 1000)
            elif action == "screenshot":
                path = self.template_resolver.resolve(handler.get("path", "error.png"))
                await self.page.screenshot(path=path)
            elif action == "retry":
                max_attempts = handler.get("max_attempts", 3)
                delay = handler.get("delay", 1000)
                # Note: retry logic would need to be handled at a higher level
                logger.info(f"[PlaywrightExecutor] Retry demandé: {max_attempts} tentatives, délai {delay}ms")
            elif action == "log":
                level = handler.get("level", "info")
                message = handler.get("message", str(error))
                getattr(logger, level)(f"[PlaywrightExecutor] {message}")
            elif action == "skip":
                logger.info("[PlaywrightExecutor] Étape ignorée après erreur")
                return
            elif action == "break":
                self._should_break = True
                return
    
    async def _execute_wait_for(self, wait_config: Dict[str, Any]):
        """Exécute une attente conditionnelle"""
        wait_config = self.template_resolver.resolve(wait_config)
        
        if "selector" in wait_config:
            state = wait_config.get("state", "visible")
            timeout = wait_config.get("timeout", 10000)
            await self.page.wait_for_selector(
                wait_config["selector"],
                state=state,
                timeout=timeout
            )
        elif "url" in wait_config:
            await self.page.wait_for_url(
                wait_config["url"],
                timeout=wait_config.get("timeout", 10000)
            )
        elif "function" in wait_config:
            await self.page.wait_for_function(
                wait_config["function"],
                timeout=wait_config.get("timeout", 10000)
            )
    
    # === Actions Playwright ===
    
    async def _action_goto(self, params: Dict[str, Any]):
        """Navigation vers une URL"""
        url = params.get("url", self.config.site_url)
        options = params.get("options", {})
        
        wait_until = options.get("wait_until", self.config.browser.wait_until)
        timeout = options.get("timeout", self.config.browser.navigation_timeout)
        
        await self.page.goto(url, wait_until=wait_until, timeout=timeout)
        logger.debug(f"[PlaywrightExecutor] Navigué vers: {url}")
    
    async def _action_click(self, params: Dict[str, Any]):
        """Clic sur un élément (selector ou role+name)."""
        options = params.get("options", {})
        loc = self._get_locator(params)
        await loc.click(
            force=options.get("force", False),
            timeout=options.get("timeout", 5000),
        )
        logger.debug("[PlaywrightExecutor] Cliqué")
    
    async def _action_fill(self, params: Dict[str, Any]):
        """Remplissage d'un champ (selector ou role+name)."""
        value = params.get("value", "")
        options = params.get("options", {})
        loc = self._get_locator(params)
        if options.get("clear", False):
            await loc.fill("")
        if self.anti_bot.get("human_typing"):
            await loc.type(value, delay=random.randint(50, 150))
        else:
            await loc.fill(value)
        logger.debug("[PlaywrightExecutor] Rempli")
    
    async def _action_select_option(self, params: Dict[str, Any]):
        """Sélection dans un select"""
        selector = params.get("selector")
        value = params.get("value")
        
        await self.page.select_option(selector, value)
        logger.debug(f"[PlaywrightExecutor] Sélectionné {value} dans {selector}")
    
    async def _action_check(self, params: Dict[str, Any]):
        """Cocher une case (selector ou role+name)."""
        options = params.get("options", {})
        loc = self._get_locator(params)
        await loc.check(timeout=options.get("timeout", 5000))
    
    async def _action_uncheck(self, params: Dict[str, Any]):
        """Décocher une case"""
        selector = params.get("selector")
        await self.page.uncheck(selector)
    
    async def _action_hover(self, params: Dict[str, Any]):
        """Survol d'un élément"""
        selector = params.get("selector")
        await self.page.hover(selector)
    
    async def _action_focus(self, params: Dict[str, Any]):
        """Focus sur un élément"""
        selector = params.get("selector")
        await self.page.focus(selector)
    
    async def _action_press(self, params: Dict[str, Any]):
        """Appui sur une touche"""
        key = params.get("key")
        selector = params.get("selector")
        
        if selector:
            await self.page.press(selector, key)
        else:
            await self.page.keyboard.press(key)
    
    async def _action_type(self, params: Dict[str, Any]):
        """Frappe au clavier"""
        text = params.get("text", "")
        delay = params.get("delay", 50)
        await self.page.keyboard.type(text, delay=delay)
    
    async def _action_wait(self, params: Dict[str, Any]):
        """Attente simple"""
        timeout = params.get("timeout", 1000)
        await asyncio.sleep(timeout / 1000)
    
    async def _action_wait_for(self, params: Dict[str, Any]):
        """Attente conditionnelle"""
        await self._execute_wait_for(params)
    
    async def _action_screenshot(self, params: Dict[str, Any]):
        """Capture d'écran"""
        path = params.get("path", f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        full_page = params.get("full_page", False)
        
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        await self.page.screenshot(path=path, full_page=full_page)
        logger.info(f"[PlaywrightExecutor] Screenshot sauvegardé: {path}")
    
    async def _action_scroll(self, params: Dict[str, Any]):
        """Défilement de la page"""
        direction = params.get("direction", "down")
        amount = params.get("amount", 500)
        selector = params.get("selector")
        
        if selector:
            element = await self.page.query_selector(selector)
            if element:
                await element.scroll_into_view_if_needed()
        else:
            if direction == "down":
                await self.page.evaluate(f"window.scrollBy(0, {amount})")
            elif direction == "up":
                await self.page.evaluate(f"window.scrollBy(0, -{amount})")
            elif direction == "bottom":
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            elif direction == "top":
                await self.page.evaluate("window.scrollTo(0, 0)")
    
    async def _action_go_back(self, params: Dict[str, Any]):
        """Retour en arrière"""
        await self.page.go_back()
    
    async def _action_reload(self, params: Dict[str, Any]):
        """Rechargement de la page"""
        await self.page.reload()
    
    async def _action_evaluate(self, params: Dict[str, Any]):
        """Exécution de JavaScript"""
        code = params.get("code", "")
        result = await self.page.evaluate(code)
        return result

    async def _action_click_filter_text(self, params: Dict[str, Any]):
        """Clic sur un élément filtré par texte exact (ex. div avec texte '0' ou '60'). selector + text + nth."""
        selector = params.get("selector", "div")
        text = str(params.get("text", "")).strip()
        exact = params.get("exact", True)
        nth = int(params.get("nth", 0))
        options = params.get("options", {})
        timeout = options.get("timeout", 5000)
        if exact and text:
            pattern = re.compile(r"^" + re.escape(text) + r"$")
        else:
            pattern = text
        loc = self.page.locator(selector).filter(has_text=pattern).nth(nth)
        await loc.click(timeout=timeout)
        logger.debug("[PlaywrightExecutor] Cliqué sur %s (text=%r, nth=%s)", selector, text, nth)

    async def _action_log(self, params: Dict[str, Any]):
        """Journalisation"""
        message = params.get("message", "")
        level = params.get("level", "info")
        getattr(logger, level)(f"[PlaywrightExecutor] {message}")
    
    async def _action_break(self, params: Dict[str, Any]):
        """Sortie de boucle"""
        self._should_break = True
    
    async def _action_click_in_iframe(self, params: Dict[str, Any]):
        """Clic dans un iframe (cookies, etc.). iframe_selector + selector ou role+name."""
        iframe_selector = params.get("iframe_selector")
        if not iframe_selector:
            raise ValueError("click_in_iframe requiert iframe_selector")
        options = params.get("options", {})
        frame = self.page.frame_locator(iframe_selector)
        role, name = params.get("role"), params.get("name")
        if role and name is not None:
            loc = frame.get_by_role(role, name=str(name))
        else:
            sel = params.get("selector")
            if not sel:
                raise ValueError("click_in_iframe requiert selector ou (role + name)")
            loc = frame.locator(sel)
        await loc.click(
            force=options.get("force", False),
            timeout=options.get("timeout", 5000),
        )
        logger.debug("[PlaywrightExecutor] Cliqué dans iframe")

    async def _action_handle_popup(self, params: Dict[str, Any]):
        """Gestion des popups (cookies, modals, etc.)"""
        popup_type = params.get("type", "cookie_banner")
        selector = params.get("selector")
        strategy = params.get("strategy", "accept")
        
        try:
            element = await self.page.query_selector(selector)
            if element:
                if strategy == "accept":
                    # Chercher un bouton d'acceptation
                    accept_selectors = [
                        f"{selector} button:has-text('Accept')",
                        f"{selector} button:has-text('Accepter')",
                        f"{selector} [class*='accept']",
                        f"{selector} [id*='accept']",
                    ]
                    for accept_sel in accept_selectors:
                        try:
                            await self.page.click(accept_sel, timeout=2000)
                            logger.debug(f"[PlaywrightExecutor] Popup accepté avec {accept_sel}")
                            return
                        except Exception:
                            continue
                elif strategy == "dismiss" or strategy == "close":
                    close_selectors = [
                        f"{selector} button:has-text('Close')",
                        f"{selector} button:has-text('Fermer')",
                        f"{selector} [class*='close']",
                        f"{selector} [aria-label='Close']",
                    ]
                    for close_sel in close_selectors:
                        try:
                            await self.page.click(close_sel, timeout=2000)
                            logger.debug(f"[PlaywrightExecutor] Popup fermé avec {close_sel}")
                            return
                        except Exception:
                            continue
            else:
                logger.debug(f"[PlaywrightExecutor] Popup non trouvé: {selector}")
        except Exception as e:
            logger.debug(f"[PlaywrightExecutor] Erreur gestion popup: {e}")
            
            # Essayer les fallbacks
            if "fallback" in params:
                for fallback in params["fallback"]:
                    try:
                        fallback_step = PlaywrightStep.from_dict(fallback.copy())
                        await self._execute_step(fallback_step)
                        return
                    except Exception:
                        continue
    
    async def _action_extract(self, params: Dict[str, Any]):
        """Extraction de données depuis un élément"""
        fields = params.get("fields", [])
        store_as = params.get("store_as")
        append = params.get("append", False)
        merge_with_item_var = params.get("merge_with_item_var")
        elem_timeout = 3000  # 3s max par champ pour éviter blocages longs
        
        extracted = {}
        for field in fields:
            name = field.get("name")
            selector = field.get("selector")
            field_type = field.get("type", "text")
            
            try:
                sel = str(selector).strip()
                if sel.startswith("xpath=") or sel.startswith("//"):
                    loc = self.page.locator(sel if sel.startswith("xpath=") else f"xpath={sel}").first
                    element = await loc.element_handle(timeout=elem_timeout)
                else:
                    element = await self.page.locator(selector).first.element_handle(timeout=elem_timeout)
                if element:
                    if field_type == "text":
                        value = await element.inner_text()
                    elif field_type == "attribute":
                        attr = field.get("attribute", "href")
                        value = await element.get_attribute(attr)
                    elif field_type == "html":
                        value = await element.inner_html()
                    else:
                        value = await element.inner_text()
                    
                    # Appliquer les transformations
                    if isinstance(value, str):
                        if field.get("transform") == "trim":
                            value = value.strip()
                        elif field.get("transform") == "absolute_url" and not value.startswith("http"):
                            parsed = urlparse(self.config.site_url)
                            origin = f"{parsed.scheme}://{parsed.netloc}"
                            value = urljoin(origin + "/", value)
                            if "#" in value:
                                value = value.split("#")[0]
                        elif field.get("transform") == "offre_id":
                            qs = parse_qs(urlparse(value).query)
                            value = (qs.get("offreId") or qs.get("offreid") or [""])[0]
                    
                    extracted[name] = value
                else:
                    extracted[name] = field.get("fallback", "")
            except Exception as e:
                if field.get("required"):
                    raise
                extracted[name] = field.get("fallback", "")
                logger.debug(f"[PlaywrightExecutor] Champ {name} non trouvé: {e}")
        
        # Merge éventuel avec l'item courant (for_each)
        if merge_with_item_var:
            item = self.template_resolver.get(merge_with_item_var)
            if isinstance(item, dict):
                extracted = {**item, **extracted}
        
        if append:
            self.extracted_data.append(extracted)
            self.template_resolver.add_to_context("extracted_offers", self.extracted_data)
        
        if store_as:
            self.template_resolver.add_to_context(store_as, extracted)
        
        return extracted
    
    async def _action_extract_list(self, params: Dict[str, Any]):
        """Extraction d'une liste d'éléments (optionnellement limitée au container)."""
        container_selector = params.get("container_selector")
        item_selector = params.get("item_selector", container_selector)
        fields = params.get("fields", [])
        metadata = params.get("metadata", {})
        store_as = params.get("store_as")
        append = params.get("append", True)
        
        if container_selector:
            container = await self.page.query_selector(container_selector)
            items = await container.query_selector_all(item_selector) if container else []
        else:
            items = await self.page.query_selector_all(item_selector)
        logger.info(f"[PlaywrightExecutor] {len(items)} éléments trouvés (container={container_selector!r}, item={item_selector!r})")
        
        extracted_items = []
        for item in items:
            item_data = {}
            
            for field in fields:
                name = field.get("name")
                selector = field.get("selector")
                field_type = field.get("type", "text")
                
                try:
                    if str(selector).strip().lower() == "self":
                        element = item
                    else:
                        element = await item.query_selector(selector)
                    if element:
                        if field_type == "text":
                            value = await element.inner_text()
                        elif field_type == "attribute":
                            attr = field.get("attribute", "href")
                            value = await element.get_attribute(attr)
                        elif field_type == "list":
                            list_items = await item.query_selector_all(field.get("item_selector", "li"))
                            value = [await li.inner_text() for li in list_items]
                        else:
                            value = await element.inner_text()
                        
                        # Transformations
                        if isinstance(value, str):
                            if field.get("transform") == "trim":
                                value = value.strip()
                            elif field.get("transform") == "absolute_url" and not value.startswith("http"):
                                parsed = urlparse(self.config.site_url)
                                origin = f"{parsed.scheme}://{parsed.netloc}"
                                value = urljoin(origin + "/", value)
                                if "#" in value:
                                    value = value.split("#")[0]
                            elif field.get("transform") == "offre_id":
                                qs = parse_qs(urlparse(value).query)
                                value = (qs.get("offreId") or qs.get("offreid") or [""])[0]
                        
                        item_data[name] = value
                    else:
                        item_data[name] = field.get("fallback", "")
                except Exception as e:
                    if field.get("required"):
                        logger.warning(f"[PlaywrightExecutor] Champ requis {name} non trouvé: {e}")
                    item_data[name] = field.get("fallback", "")
            
            # Ajouter les métadonnées
            item_data.update(self.template_resolver.resolve(metadata))
            
            extracted_items.append(item_data)
        
        # Dédupliquer par id (offreId) ou URL (même offre peut apparaître plusieurs fois sur la page)
        if store_as and extracted_items:
            seen = set()
            unique_items = []
            for it in extracted_items:
                key = it.get("id") or it.get("offer_id") or it.get("url") or ""
                if not key:
                    unique_items.append(it)
                elif key not in seen:
                    seen.add(key)
                    unique_items.append(it)
            if len(unique_items) < len(extracted_items):
                logger.info(f"[PlaywrightExecutor] {len(unique_items)} liens uniques après déduplication (était {len(extracted_items)})")
            extracted_items = unique_items
        
        if append:
            self.extracted_data.extend(extracted_items)
            self.template_resolver.add_to_context("extracted_offers", self.extracted_data)
        
        if store_as:
            self.template_resolver.add_to_context(store_as, extracted_items)
        
        logger.info(f"[PlaywrightExecutor] {len(extracted_items)} éléments extraits")
        return extracted_items
    
    async def _action_paginate(self, params: Dict[str, Any]):
        """Gestion de la pagination"""
        strategy = params.get("strategy", "click_next")
        max_pages = params.get("max_pages", 5)
        next_button = params.get("next_button", {})
        
        current_page = 1
        
        while current_page < max_pages:
            if strategy == "click_next":
                try:
                    selector = next_button.get("selector")
                    element = await self.page.query_selector(selector)
                    
                    if not element:
                        logger.info("[PlaywrightExecutor] Plus de pages disponibles")
                        break
                    
                    await element.click()
                    
                    # Attendre le chargement
                    if "wait_for" in next_button:
                        await self._execute_wait_for(next_button["wait_for"])
                    
                    current_page += 1
                    logger.debug(f"[PlaywrightExecutor] Page {current_page} chargée")
                    
                    # Appliquer les délais
                    await self._apply_delays()
                    
                except Exception as e:
                    logger.info(f"[PlaywrightExecutor] Fin de pagination: {e}")
                    break
            
            elif strategy == "scroll_load":
                # Scroll infini
                previous_height = await self.page.evaluate("document.body.scrollHeight")
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
                new_height = await self.page.evaluate("document.body.scrollHeight")
                
                if new_height == previous_height:
                    break
                
                current_page += 1
        
        # Exécuter on_no_more si défini
        if "on_no_more" in params:
            for handler in params["on_no_more"]:
                handler_step = PlaywrightStep.from_dict(handler.copy())
                await self._execute_step(handler_step)
    
    async def _action_for_each(self, params: Dict[str, Any]):
        """Boucle sur des éléments"""
        items_key = params.get("items", "extracted_offers")
        item_var = params.get("item_var", "item")
        steps = params.get("steps", [])
        limit = params.get("limit")
        skip_existing = params.get("skip_existing", False)
        
        # Récupérer les items depuis le contexte
        items = self.template_resolver._get_nested_value(items_key.replace("{{", "").replace("}}", ""))
        
        if not items:
            logger.warning(f"[PlaywrightExecutor] Aucun item trouvé pour {items_key}")
            return
        
        # Filtrer les annonces déjà scrapées (nouvelles uniquement)
        if skip_existing:
            existing = set(self.template_resolver.get("existing_offer_ids") or [])
            before = len(items)
            items = [it for it in items if (it.get("id") or it.get("offer_id")) not in existing]
            if len(items) < before:
                logger.info(f"[PlaywrightExecutor] {len(items)} annonces nouvelles à scraper (skippé {before - len(items)} déjà existantes)")
        
        if isinstance(limit, int) and limit >= 0:
            items = items[:limit]
        for i, item in enumerate(items):
            if self._should_break:
                break
            
            # Ajouter l'item au contexte
            self.template_resolver.add_to_context(item_var, item)
            self.template_resolver.add_to_context("loop_index", i)
            
            # Exécuter les étapes
            for step_data in steps:
                step = PlaywrightStep.from_dict(step_data.copy())
                await self._execute_step(step)
                await self._apply_delays()
    
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
                logger.warning(f"[PlaywrightExecutor] Erreur conversion offre {i}: {e}")
        
        return offers
