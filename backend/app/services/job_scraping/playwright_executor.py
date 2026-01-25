"""
Exécuteur Playwright pour les configurations de scraping.

Exécute les étapes définies dans les fichiers de configuration markdown
en utilisant l'API Playwright Python.
"""

import os
import random
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

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
                        await self._execute_step(step)
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
    
    async def _execute_step(self, step: PlaywrightStep):
        """Exécute une étape Playwright"""
        # Résoudre les templates dans les paramètres
        params = self.template_resolver.resolve(step.params)
        
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
        """Clic sur un élément"""
        selector = params.get("selector")
        options = params.get("options", {})
        
        await self.page.click(
            selector,
            force=options.get("force", False),
            timeout=options.get("timeout", 5000),
        )
        logger.debug(f"[PlaywrightExecutor] Cliqué sur: {selector}")
    
    async def _action_fill(self, params: Dict[str, Any]):
        """Remplissage d'un champ"""
        selector = params.get("selector")
        value = params.get("value", "")
        options = params.get("options", {})
        
        if options.get("clear", False):
            await self.page.fill(selector, "")
        
        if self.anti_bot.get("human_typing"):
            # Simulation de frappe humaine
            await self.page.type(selector, value, delay=random.randint(50, 150))
        else:
            await self.page.fill(selector, value)
        
        logger.debug(f"[PlaywrightExecutor] Rempli {selector}")
    
    async def _action_select_option(self, params: Dict[str, Any]):
        """Sélection dans un select"""
        selector = params.get("selector")
        value = params.get("value")
        
        await self.page.select_option(selector, value)
        logger.debug(f"[PlaywrightExecutor] Sélectionné {value} dans {selector}")
    
    async def _action_check(self, params: Dict[str, Any]):
        """Cocher une case"""
        selector = params.get("selector")
        await self.page.check(selector)
    
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
    
    async def _action_log(self, params: Dict[str, Any]):
        """Journalisation"""
        message = params.get("message", "")
        level = params.get("level", "info")
        getattr(logger, level)(f"[PlaywrightExecutor] {message}")
    
    async def _action_break(self, params: Dict[str, Any]):
        """Sortie de boucle"""
        self._should_break = True
    
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
        
        extracted = {}
        for field in fields:
            name = field.get("name")
            selector = field.get("selector")
            field_type = field.get("type", "text")
            
            try:
                element = await self.page.query_selector(selector)
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
                    if field.get("transform") == "trim":
                        value = value.strip() if value else ""
                    if field.get("transform") == "absolute_url" and value and not value.startswith("http"):
                        value = f"{self.config.site_url.rstrip('/')}/{value.lstrip('/')}"
                    
                    extracted[name] = value
                else:
                    extracted[name] = field.get("fallback", "")
            except Exception as e:
                if field.get("required"):
                    raise
                extracted[name] = field.get("fallback", "")
                logger.debug(f"[PlaywrightExecutor] Champ {name} non trouvé: {e}")
        
        return extracted
    
    async def _action_extract_list(self, params: Dict[str, Any]):
        """Extraction d'une liste d'éléments"""
        container_selector = params.get("container_selector")
        item_selector = params.get("item_selector", container_selector)
        fields = params.get("fields", [])
        metadata = params.get("metadata", {})
        
        items = await self.page.query_selector_all(item_selector)
        logger.info(f"[PlaywrightExecutor] {len(items)} éléments trouvés avec {item_selector}")
        
        extracted_items = []
        for item in items:
            item_data = {}
            
            for field in fields:
                name = field.get("name")
                selector = field.get("selector")
                field_type = field.get("type", "text")
                
                try:
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
                            if field.get("transform") == "absolute_url" and value and not value.startswith("http"):
                                value = f"{self.config.site_url.rstrip('/')}/{value.lstrip('/')}"
                        
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
        
        self.extracted_data.extend(extracted_items)
        self.template_resolver.add_to_context("extracted_offers", self.extracted_data)
        
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
        
        # Récupérer les items depuis le contexte
        items = self.template_resolver._get_nested_value(items_key.replace("{{", "").replace("}}", ""))
        
        if not items:
            logger.warning(f"[PlaywrightExecutor] Aucun item trouvé pour {items_key}")
            return
        
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
                    id=data.get("source_id", data.get("id", f"{self.config.name}-{i}")),
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
