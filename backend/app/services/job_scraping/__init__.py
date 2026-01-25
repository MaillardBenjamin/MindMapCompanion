"""
Module de scraping d'offres d'emploi.

Ce module fournit :
- Un parser de configuration markdown pour les scrapers
- Un exécuteur Playwright basé sur les configurations
- Un gestionnaire de stockage pour les offres en markdown
- Un service orchestrant le tout
- Un scheduler pour le nettoyage automatique
"""

from app.services.job_scraping.scraper_config_parser import ScraperConfigParser
from app.services.job_scraping.storage_manager import StorageManager, StorageConfig, JobOffer
from app.services.job_scraping.playwright_executor import PlaywrightExecutor
from app.services.job_scraping.job_scraping_service import JobScrapingService, get_job_scraping_service
from app.services.job_scraping.cleanup_scheduler import JobCleanupScheduler, get_cleanup_scheduler

__all__ = [
    "ScraperConfigParser",
    "StorageManager",
    "StorageConfig",
    "JobOffer",
    "PlaywrightExecutor",
    "JobScrapingService",
    "get_job_scraping_service",
    "JobCleanupScheduler",
    "get_cleanup_scheduler",
]
