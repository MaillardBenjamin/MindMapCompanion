"""
Scheduler pour le nettoyage automatique des offres d'emploi.

Intègre avec le scheduler existant pour exécuter le nettoyage
selon les configurations définies dans les scrapers.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.services.job_scraping.storage_manager import StorageManager, StorageConfig
from app.services.job_scraping.scraper_config_parser import ScraperConfigParser

logger = logging.getLogger(__name__)


class JobCleanupScheduler:
    """
    Scheduler pour le nettoyage des anciennes offres d'emploi.
    
    Parcourt les configurations des scrapers et nettoie les offres
    selon les paramètres de rétention configurés.
    """
    
    def __init__(
        self,
        examples_dir: Optional[Path] = None,
        project_root: Optional[Path] = None,
    ):
        """
        Initialise le scheduler.
        
        Args:
            examples_dir: Répertoire contenant les configurations
            project_root: Répertoire racine du projet
        """
        if examples_dir is None:
            examples_dir = Path(__file__).parent.parent.parent / "agent_configs"
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent.parent
        
        self.examples_dir = examples_dir
        self.project_root = project_root
        self.config_parser = ScraperConfigParser(examples_dir)
    
    def get_cleanup_jobs(self) -> List[Dict[str, Any]]:
        """
        Récupère les jobs de nettoyage depuis les configurations.
        
        Returns:
            Liste des jobs de nettoyage avec leurs paramètres
        """
        jobs = []
        
        # Parcourir les configurations de scrapers
        for config_path in self.config_parser.list_available_configs("scrapers"):
            try:
                config = self.config_parser.load_config(str(config_path.relative_to(self.examples_dir)))
                
                if config.storage.cleanup_enabled:
                    jobs.append({
                        "name": f"cleanup_{config.name.lower().replace(' ', '_')}",
                        "scraper_name": config.name,
                        "base_dir": config.storage.base_dir,
                        "retention_days": config.storage.retention_days,
                        "schedule": config.storage.cleanup_schedule,
                        "archive_dir": config.storage.archive_dir,
                    })
                    logger.debug(f"[JobCleanupScheduler] Job de nettoyage trouvé: {config.name}")
            except Exception as e:
                logger.warning(f"[JobCleanupScheduler] Erreur lecture config {config_path}: {e}")
        
        return jobs
    
    def run_cleanup(
        self,
        base_dir: Optional[str] = None,
        retention_days: Optional[int] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Exécute le nettoyage des offres.
        
        Args:
            base_dir: Répertoire de base à nettoyer (optionnel, tous si non spécifié)
            retention_days: Jours de rétention (optionnel, utilise la config sinon)
            dry_run: Si True, simule le nettoyage sans supprimer
        
        Returns:
            Statistiques du nettoyage
        """
        logger.info(f"[JobCleanupScheduler] Démarrage du nettoyage (dry_run={dry_run})")
        
        total_stats = {
            "start_time": datetime.now().isoformat(),
            "scrapers_processed": 0,
            "total_directories_archived": 0,
            "total_directories_deleted": 0,
            "total_files_deleted": 0,
            "errors": [],
            "dry_run": dry_run,
        }
        
        # Récupérer les jobs de nettoyage
        jobs = self.get_cleanup_jobs()
        
        if base_dir:
            # Filtrer pour le répertoire spécifié
            jobs = [j for j in jobs if j["base_dir"] == base_dir or base_dir in j["base_dir"]]
        
        if not jobs:
            logger.info("[JobCleanupScheduler] Aucun job de nettoyage à exécuter")
            return total_stats
        
        for job in jobs:
            try:
                # Créer la configuration de stockage
                storage_config = StorageConfig(
                    base_dir=job["base_dir"],
                    retention_days=retention_days or job["retention_days"],
                    cleanup_enabled=True,
                    archive_dir=job.get("archive_dir"),
                )
                
                storage_manager = StorageManager(storage_config, self.project_root)
                
                # Exécuter le nettoyage
                stats = storage_manager.cleanup_old_files(dry_run=dry_run)
                
                # Agréger les statistiques
                total_stats["scrapers_processed"] += 1
                total_stats["total_directories_archived"] += stats.get("directories_archived", 0)
                total_stats["total_directories_deleted"] += stats.get("directories_deleted", 0)
                total_stats["total_files_deleted"] += stats.get("files_deleted", 0)
                
                if stats.get("errors"):
                    total_stats["errors"].extend([f"{job['scraper_name']}: {e}" for e in stats["errors"]])
                
                logger.info(f"[JobCleanupScheduler] Nettoyage {job['scraper_name']}: {stats.get('files_deleted', 0)} fichiers")
                
            except Exception as e:
                error_msg = f"{job['scraper_name']}: {str(e)}"
                total_stats["errors"].append(error_msg)
                logger.error(f"[JobCleanupScheduler] Erreur nettoyage {job['scraper_name']}: {e}", exc_info=True)
        
        total_stats["end_time"] = datetime.now().isoformat()
        
        logger.info(f"[JobCleanupScheduler] Nettoyage terminé: {total_stats}")
        return total_stats
    
    def run_cleanup_for_scraper(
        self,
        scraper_name: str,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Exécute le nettoyage pour un scraper spécifique.
        
        Args:
            scraper_name: Nom du scraper
            dry_run: Si True, simule le nettoyage
        
        Returns:
            Statistiques du nettoyage
        """
        jobs = self.get_cleanup_jobs()
        
        matching_jobs = [
            j for j in jobs
            if scraper_name.lower() in j["scraper_name"].lower()
        ]
        
        if not matching_jobs:
            return {
                "success": False,
                "error": f"Aucun scraper trouvé pour: {scraper_name}",
            }
        
        job = matching_jobs[0]
        
        storage_config = StorageConfig(
            base_dir=job["base_dir"],
            retention_days=job["retention_days"],
            cleanup_enabled=True,
            archive_dir=job.get("archive_dir"),
        )
        
        storage_manager = StorageManager(storage_config, self.project_root)
        stats = storage_manager.cleanup_old_files(dry_run=dry_run)
        
        return stats
    
    def get_storage_summary(self) -> Dict[str, Any]:
        """
        Récupère un résumé de l'état du stockage.
        
        Returns:
            Statistiques de stockage par scraper
        """
        summary = {
            "timestamp": datetime.now().isoformat(),
            "scrapers": {},
            "total_files": 0,
            "total_size_bytes": 0,
        }
        
        for job in self.get_cleanup_jobs():
            try:
                storage_config = StorageConfig(
                    base_dir=job["base_dir"],
                    retention_days=job["retention_days"],
                )
                
                storage_manager = StorageManager(storage_config, self.project_root)
                stats = storage_manager.get_storage_stats()
                
                summary["scrapers"][job["scraper_name"]] = {
                    "base_dir": stats["base_dir"],
                    "file_count": stats["total_files"],
                    "size_bytes": stats["total_size_bytes"],
                    "retention_days": job["retention_days"],
                }
                
                summary["total_files"] += stats["total_files"]
                summary["total_size_bytes"] += stats["total_size_bytes"]
                
            except Exception as e:
                logger.warning(f"[JobCleanupScheduler] Erreur stats {job['scraper_name']}: {e}")
        
        return summary


# Instance singleton
_cleanup_scheduler: Optional[JobCleanupScheduler] = None


def get_cleanup_scheduler() -> JobCleanupScheduler:
    """Retourne l'instance singleton du scheduler de nettoyage"""
    global _cleanup_scheduler
    if _cleanup_scheduler is None:
        _cleanup_scheduler = JobCleanupScheduler()
    return _cleanup_scheduler


async def run_scheduled_cleanup():
    """
    Fonction à appeler par le scheduler APScheduler.
    
    Exécute le nettoyage automatique des offres d'emploi.
    """
    scheduler = get_cleanup_scheduler()
    stats = scheduler.run_cleanup(dry_run=False)
    
    logger.info(f"[ScheduledCleanup] Nettoyage automatique terminé: {stats['total_files_deleted']} fichiers supprimés")
    
    return stats
