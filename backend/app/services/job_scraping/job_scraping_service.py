"""
Service de scraping d'offres d'emploi.

Orchestre le scraping en utilisant :
- ScraperConfigParser pour charger les configurations
- PlaywrightExecutor pour exécuter les instructions
- StorageManager pour sauvegarder les offres
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from app.services.job_scraping.scraper_config_parser import ScraperConfigParser, ScraperConfig
from app.services.job_scraping.playwright_executor import PlaywrightExecutor
from app.services.job_scraping.storage_manager import StorageManager, StorageConfig, JobOffer

logger = logging.getLogger(__name__)


@dataclass
class ScrapingResult:
    """Résultat d'un scraping"""
    source: str
    offers_count: int
    offers: List[JobOffer]
    saved_files: List[Path]
    errors: List[str]
    success: bool


class JobScrapingService:
    """
    Service principal pour le scraping d'offres d'emploi.
    
    Utilise les configurations markdown pour scraper sans code.
    """
    
    def __init__(self, examples_dir: Optional[Path] = None, project_root: Optional[Path] = None):
        """
        Initialise le service.
        
        Args:
            examples_dir: Répertoire contenant les fichiers de configuration
            project_root: Répertoire racine du projet
        """
        if examples_dir is None:
            examples_dir = Path(__file__).parent.parent.parent / "agent_configs"
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent.parent
        
        self.examples_dir = examples_dir
        self.project_root = project_root
        self.config_parser = ScraperConfigParser(examples_dir)
    
    async def scrape_with_config(
        self,
        config_path: str,
        search_params: Optional[Dict[str, Any]] = None,
        save_to_files: bool = True,
    ) -> ScrapingResult:
        """
        Scrape les offres en utilisant une configuration markdown.
        
        Args:
            config_path: Chemin du fichier de configuration
            search_params: Paramètres de recherche (keywords, location, etc.)
            save_to_files: Si True, sauvegarde les offres en fichiers markdown
        
        Returns:
            Résultat du scraping
        """
        errors = []
        offers = []
        saved_files = []
        
        logger.info("[JobScrapingService] 🔧 scrape_with_config ENTRY: config_path=%s, search_params keys=%s",
            config_path, list((search_params or {}).keys()))
        try:
            # Charger la configuration
            config = self.config_parser.load_config(config_path)
            logger.info(f"[JobScrapingService] Configuration chargée: {config.name}")
            
            # Valider la configuration
            is_valid, validation_errors = self.config_parser.validate_config(config)
            if not is_valid:
                errors.extend(validation_errors)
                logger.error(f"[JobScrapingService] Configuration invalide: {validation_errors}")
                return ScrapingResult(
                    source=config.name,
                    offers_count=0,
                    offers=[],
                    saved_files=[],
                    errors=errors,
                    success=False,
                )
            
            # Préparer le contexte : IDs existants pour ne scraper que les nouvelles annonces
            source_name = config.name.lower().replace(" ", "-").replace("_", "-")
            if "scraper" in source_name:
                source_name = source_name.replace("-scraper", "").replace("scraper-", "")
            storage_config = StorageConfig.from_dict({
                "base_dir": config.storage.base_dir,
                "subdir_pattern": config.storage.subdir_pattern,
                "file_pattern": config.storage.file_pattern,
                "archive_dir": config.storage.archive_dir,
                "retention_days": config.storage.retention_days,
                "cleanup_enabled": config.storage.cleanup_enabled,
            })
            storage_manager = StorageManager(storage_config, self.project_root)
            existing_ids = storage_manager.get_existing_offer_ids(source_name)
            context = dict(search_params or {})
            context["existing_offer_ids"] = existing_ids
            if existing_ids:
                logger.info("[JobScrapingService] %d annonces déjà en base, scraping des nouvelles uniquement", len(existing_ids))
            
            # Créer et exécuter l'exécuteur Playwright
            logger.info("[JobScrapingService] 🚀 Exécution Playwright pour %s...", config.name)
            executor = PlaywrightExecutor(config, context=context)
            offers = await executor.execute(search_params)
            logger.info("[JobScrapingService] ✅ Playwright terminé pour %s: %d offres", config.name, len(offers))
            
            # Sauvegarder les offres si demandé
            if save_to_files and offers:
                saved_files = storage_manager.save_offers(offers, source_name)
                logger.info("[JobScrapingService] %d fichiers sauvegardés dans %s", len(saved_files), storage_manager.base_path)
                for p in saved_files[:3]:
                    logger.info("[JobScrapingService]   → %s", p)
                if len(saved_files) > 3:
                    logger.info("[JobScrapingService]   ... et %d autres", len(saved_files) - 3)
            
            return ScrapingResult(
                source=config.name,
                offers_count=len(offers),
                offers=offers,
                saved_files=saved_files,
                errors=errors,
                success=True,
            )
            
        except FileNotFoundError as e:
            errors.append(f"Fichier de configuration non trouvé: {e}")
            logger.error(f"[JobScrapingService] {errors[-1]}")
        except Exception as e:
            errors.append(f"Erreur lors du scraping: {e}")
            logger.error(f"[JobScrapingService] {errors[-1]}", exc_info=True)
        
        return ScrapingResult(
            source=config_path,
            offers_count=0,
            offers=[],
            saved_files=[],
            errors=errors,
            success=False,
        )
    
    async def scrape_multiple(
        self,
        config_paths: List[str],
        search_params: Optional[Dict[str, Any]] = None,
        save_to_files: bool = True,
    ) -> Dict[str, ScrapingResult]:
        """
        Scrape depuis plusieurs sources.
        
        Args:
            config_paths: Liste des chemins de configuration
            search_params: Paramètres de recherche communs
            save_to_files: Si True, sauvegarde les offres en fichiers markdown
        
        Returns:
            Dictionnaire {source: résultat}
        """
        logger.info(
            "[JobScrapingService] 🔧 scrape_multiple ENTRY: config_paths=%s, search_params=%s, save_to_files=%s",
            config_paths, search_params, save_to_files,
        )
        results = {}
        
        for config_path in config_paths:
            logger.info("[JobScrapingService] 📂 Scraping source: %s ...", config_path)
            result = await self.scrape_with_config(config_path, search_params, save_to_files)
            results[result.source] = result
            logger.info("[JobScrapingService] 📂 Source %s terminée: %d offres, success=%s",
                config_path, result.offers_count, result.success)
        
        # Résumé
        total_offers = sum(r.offers_count for r in results.values())
        successful = sum(1 for r in results.values() if r.success)
        logger.info(f"[JobScrapingService] Scraping terminé: {total_offers} offres de {successful}/{len(results)} sources")
        
        return results
    
    async def scrape_from_agent_config(
        self,
        agent_config: Dict[str, Any],
        search_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, ScrapingResult]:
        """
        Scrape en utilisant la configuration d'un agent.
        
        Lit les scrapers configurés dans le frontmatter de l'agent.
        
        Args:
            agent_config: Configuration de l'agent (parsée depuis le markdown)
            search_params: Paramètres de recherche
        
        Returns:
            Dictionnaire {source: résultat}
        """
        # Récupérer les chemins des scrapers depuis la config de l'agent
        scraper_paths = agent_config.get("scrapers", [])
        
        if not scraper_paths:
            logger.warning("[JobScrapingService] Aucun scraper configuré dans l'agent")
            return {}
        
        # Utiliser la config de storage de l'agent si disponible
        storage_override = agent_config.get("storage")
        
        logger.info(f"[JobScrapingService] Scraping avec {len(scraper_paths)} scrapers depuis la config agent")
        
        return await self.scrape_multiple(scraper_paths, search_params, save_to_files=True)
    
    def list_available_scrapers(self) -> List[Dict[str, Any]]:
        """
        Liste les scrapers disponibles.
        
        Returns:
            Liste de dictionnaires avec les infos de chaque scraper
        """
        scrapers = []
        
        for config_path in self.config_parser.list_available_configs("scrapers"):
            try:
                config = self.config_parser.load_config(str(config_path.relative_to(self.examples_dir)))
                scrapers.append({
                    "path": str(config_path.relative_to(self.examples_dir)),
                    "name": config.name,
                    "site_url": config.site_url,
                    "steps_count": len(config.steps),
                    "requires_auth": bool(config.credentials.email_env),
                })
            except Exception as e:
                logger.warning(f"[JobScrapingService] Erreur lecture config {config_path}: {e}")
        
        return scrapers
    
    def get_scraper_details(self, config_path: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les détails d'un scraper.
        
        Args:
            config_path: Chemin du fichier de configuration
        
        Returns:
            Dictionnaire avec les détails du scraper
        """
        try:
            config = self.config_parser.load_config(config_path)
            return {
                "name": config.name,
                "site_url": config.site_url,
                "browser": {
                    "headless": config.browser.headless,
                    "timeout": config.browser.timeout,
                },
                "storage": {
                    "base_dir": config.storage.base_dir,
                    "subdir_pattern": config.storage.subdir_pattern,
                    "retention_days": config.storage.retention_days,
                },
                "credentials": {
                    "required": bool(config.credentials.email_env),
                    "env_vars": self.config_parser.get_required_env_vars(config),
                },
                "steps_count": len(config.steps),
                "anti_bot": config.anti_bot,
                "rate_limiting": config.rate_limiting,
            }
        except Exception as e:
            logger.error(f"[JobScrapingService] Erreur lecture config {config_path}: {e}")
            return None


# Instance singleton
_job_scraping_service: Optional[JobScrapingService] = None


def get_job_scraping_service() -> JobScrapingService:
    """Retourne l'instance singleton du service de scraping"""
    global _job_scraping_service
    if _job_scraping_service is None:
        _job_scraping_service = JobScrapingService()
    return _job_scraping_service
