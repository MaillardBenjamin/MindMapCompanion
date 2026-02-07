"""
Gestionnaire de stockage pour les offres d'emploi.

Gère :
- Création de sous-répertoires selon un pattern configurable
- Sauvegarde des offres en markdown avec frontmatter
- Archivage des anciennes offres
- Nettoyage automatique selon retention_days
"""

import os
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class JobOffer:
    """Représente une offre d'emploi extraite"""
    id: str
    title: str
    company: str
    location: str
    url: str
    source: str
    description: str = ""
    salary: Optional[str] = None
    contract_type: Optional[str] = None
    publish_date: Optional[str] = None
    requirements: List[str] = field(default_factory=list)
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_markdown(self) -> str:
        """Convertit l'offre en markdown avec frontmatter YAML"""
        # Frontmatter
        frontmatter_lines = [
            "---",
            f"id: {self.id}",
            f"source: {self.source}",
            f"scraped_at: {self.scraped_at}",
            f"url: {self.url}",
        ]
        if self.publish_date:
            frontmatter_lines.append(f"publish_date: {self.publish_date}")
        if self.salary:
            frontmatter_lines.append(f"salary: \"{self.salary}\"")
        if self.contract_type:
            frontmatter_lines.append(f"contract_type: {self.contract_type}")
        frontmatter_lines.append("---")
        frontmatter = "\n".join(frontmatter_lines)
        
        # Corps du markdown
        body_parts = [
            f"# {self.title}",
            "",
            f"**Entreprise** : {self.company}",
            f"**Localisation** : {self.location}",
        ]
        
        if self.salary:
            body_parts.append(f"**Salaire** : {self.salary}")
        if self.contract_type:
            body_parts.append(f"**Type de contrat** : {self.contract_type}")
        
        body_parts.extend([
            f"**Source** : {self.source}",
            "",
            "## Description",
            "",
            self.description if self.description else "*Aucune description disponible*",
        ])

        missions = self.metadata.get("missions", "")
        if missions and str(missions).strip():
            body_parts.extend(["", "## Quelles sont les missions ?", "", str(missions).strip()])
        profil_ideal = self.metadata.get("profil_ideal", "")
        if profil_ideal and str(profil_ideal).strip():
            body_parts.extend(["", "## Quel est le profil idéal ?", "", str(profil_ideal).strip()])
        infos = self.metadata.get("informations_complementaires", "")
        if infos and str(infos).strip():
            body_parts.extend(["", "## Informations complémentaires", "", str(infos).strip()])
        
        if self.requirements:
            body_parts.extend([
                "",
                "## Compétences requises",
                "",
            ])
            for req in self.requirements:
                body_parts.append(f"- {req}")
        
        body_parts.extend([
            "",
            "---",
            f"[Voir l'offre originale]({self.url})",
        ])
        
        body = "\n".join(body_parts)
        
        return f"{frontmatter}\n\n{body}\n"


@dataclass
class StorageConfig:
    """Configuration du stockage des offres"""
    base_dir: str
    subdir_pattern: str = "{date}"  # {date}, {date}/{hour}, {source}, etc.
    file_pattern: str = "{title_slug}-{id}.md"
    archive_dir: Optional[str] = None
    retention_days: int = 30
    cleanup_enabled: bool = True
    cleanup_schedule: str = "0 2 * * 0"  # Cron expression
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StorageConfig":
        """Crée une configuration depuis un dictionnaire"""
        return cls(
            base_dir=data.get("base_dir", "data/job_offers"),
            subdir_pattern=data.get("subdir_pattern", "{date}"),
            file_pattern=data.get("file_pattern", "{title_slug}-{id}.md"),
            archive_dir=data.get("archive_dir"),
            retention_days=data.get("retention_days", 30),
            cleanup_enabled=data.get("cleanup_enabled", True),
            cleanup_schedule=data.get("cleanup_schedule", "0 2 * * 0"),
        )


class StorageManager:
    """Gestionnaire de stockage des offres d'emploi en fichiers markdown"""
    
    def __init__(self, config: StorageConfig, project_root: Optional[Path] = None):
        """
        Initialise le gestionnaire de stockage.
        
        Args:
            config: Configuration du stockage
            project_root: Répertoire racine du projet (défaut: backend/)
        """
        self.config = config
        
        if project_root is None:
            # Remonter depuis le fichier actuel jusqu'à backend/
            project_root = Path(__file__).parent.parent.parent.parent
        
        self.project_root = project_root
        self.base_path = project_root / config.base_dir
        self.archive_path = project_root / config.archive_dir if config.archive_dir else self.base_path / "archive"
        
        # Créer les répertoires si nécessaire
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.archive_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"[StorageManager] Initialisé avec base_dir: {self.base_path}")
    
    def _slugify(self, text: str) -> str:
        """Convertit un texte en slug URL-safe"""
        try:
            from slugify import slugify
            return slugify(text, max_length=50)
        except ImportError:
            # Fallback si python-slugify n'est pas disponible
            import re
            text = text.lower()
            text = re.sub(r'[^\w\s-]', '', text)
            text = re.sub(r'[\s_-]+', '-', text)
            text = text.strip('-')
            return text[:50]
    
    def _format_pattern(self, pattern: str, offer: JobOffer, source: str) -> str:
        """Formate un pattern avec les variables disponibles"""
        now = datetime.now()
        
        replacements = {
            "{date}": now.strftime("%Y-%m-%d"),
            "{hour}": now.strftime("%H"),
            "{year}": now.strftime("%Y"),
            "{month}": now.strftime("%m"),
            "{day}": now.strftime("%d"),
            "{source}": source,
            "{id}": offer.id,
            "{title_slug}": self._slugify(offer.title),
            "{company_slug}": self._slugify(offer.company),
            "{timestamp}": now.strftime("%Y%m%d_%H%M%S"),
        }
        
        result = pattern
        for key, value in replacements.items():
            result = result.replace(key, value)
        
        return result
    
    def get_storage_path(self, offer: JobOffer, source: str) -> Path:
        """
        Calcule le chemin complet pour stocker une offre.
        
        Args:
            offer: L'offre à stocker
            source: Le nom de la source (ex. cadre-emploi)
        
        Returns:
            Le chemin complet du fichier markdown
        """
        # Formater le sous-répertoire
        subdir = self._format_pattern(self.config.subdir_pattern, offer, source)
        
        # Formater le nom de fichier
        filename = self._format_pattern(self.config.file_pattern, offer, source)
        
        # Construire le chemin complet (subdir vide = pas de sous-répertoire)
        if subdir:
            full_path = self.base_path / source / subdir / filename
        else:
            full_path = self.base_path / source / filename
        
        return full_path
    
    def save_offer(self, offer: JobOffer, source: str) -> Path:
        """
        Sauvegarde une offre en fichier markdown.
        
        Args:
            offer: L'offre à sauvegarder
            source: Le nom de la source
        
        Returns:
            Le chemin du fichier créé
        """
        file_path = self.get_storage_path(offer, source)
        
        # Créer le répertoire parent si nécessaire
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Générer le contenu markdown
        markdown_content = offer.to_markdown()
        
        # Écrire le fichier
        file_path.write_text(markdown_content, encoding="utf-8")
        
        logger.info(f"[StorageManager] Offre sauvegardée: {file_path}")
        
        return file_path
    
    def save_offers(self, offers: List[JobOffer], source: str) -> List[Path]:
        """
        Sauvegarde plusieurs offres.
        
        Args:
            offers: Liste des offres à sauvegarder
            source: Le nom de la source
        
        Returns:
            Liste des chemins des fichiers créés
        """
        saved_paths = []
        for offer in offers:
            try:
                path = self.save_offer(offer, source)
                saved_paths.append(path)
            except Exception as e:
                logger.error(f"[StorageManager] Erreur lors de la sauvegarde de l'offre {offer.id}: {e}")
        
        logger.info(f"[StorageManager] {len(saved_paths)}/{len(offers)} offres sauvegardées pour {source}")
        return saved_paths
    
    def list_offers(self, source: Optional[str] = None, since: Optional[datetime] = None) -> List[Path]:
        """
        Liste les fichiers d'offres stockés.
        
        Args:
            source: Filtrer par source (optionnel)
            since: Filtrer les offres depuis une date (optionnel)
        
        Returns:
            Liste des chemins des fichiers d'offres
        """
        search_path = self.base_path / source if source else self.base_path
        
        if not search_path.exists():
            return []
        
        files = []
        for file_path in search_path.rglob("*.md"):
            # Ignorer les fichiers dans le répertoire archive
            if "archive" in str(file_path):
                continue
            
            if since:
                # Vérifier la date de modification
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mtime < since:
                    continue
            
            files.append(file_path)
        
        return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)
    
    def get_existing_offer_ids(self, source: str) -> Set[str]:
        """
        Retourne les IDs des offres déjà sauvegardées pour une source.
        Utilisé pour ne scraper que les nouvelles annonces.
        """
        search_path = self.base_path / source
        if not search_path.exists():
            return set()
        ids_ = set()
        for f in search_path.rglob("*.md"):
            if "archive" in str(f):
                continue
            ids_.add(f.stem)
        return ids_
    
    def read_offer(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Lit une offre depuis un fichier markdown.
        
        Args:
            file_path: Chemin du fichier
        
        Returns:
            Dictionnaire avec le contenu de l'offre (frontmatter + body)
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Parser le frontmatter YAML
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    import yaml
                    frontmatter = yaml.safe_load(parts[1])
                    body = parts[2].strip()
                    return {
                        "frontmatter": frontmatter,
                        "body": body,
                        "path": str(file_path),
                    }
            
            return {"body": content, "path": str(file_path)}
            
        except Exception as e:
            logger.error(f"[StorageManager] Erreur lors de la lecture de {file_path}: {e}")
            return None
    
    def archive_directory(self, dir_path: Path) -> Optional[Path]:
        """
        Archive un répertoire avant suppression.
        
        Args:
            dir_path: Répertoire à archiver
        
        Returns:
            Chemin de l'archive créée ou None en cas d'erreur
        """
        if not dir_path.exists():
            return None
        
        try:
            # Créer un nom d'archive unique
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            relative_path = dir_path.relative_to(self.base_path)
            archive_name = str(relative_path).replace("/", "_").replace("\\", "_")
            archive_path = self.archive_path / f"{archive_name}_{timestamp}"
            
            # Copier le répertoire vers l'archive
            shutil.copytree(dir_path, archive_path)
            
            logger.info(f"[StorageManager] Répertoire archivé: {dir_path} -> {archive_path}")
            return archive_path
            
        except Exception as e:
            logger.error(f"[StorageManager] Erreur lors de l'archivage de {dir_path}: {e}")
            return None
    
    def cleanup_old_files(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Nettoie les fichiers plus anciens que retention_days.
        
        Args:
            dry_run: Si True, ne supprime pas réellement les fichiers
        
        Returns:
            Statistiques du nettoyage
        """
        if not self.config.cleanup_enabled:
            logger.info("[StorageManager] Nettoyage désactivé dans la configuration")
            return {"enabled": False}
        
        cutoff_date = datetime.now() - timedelta(days=self.config.retention_days)
        
        stats = {
            "cutoff_date": cutoff_date.isoformat(),
            "retention_days": self.config.retention_days,
            "directories_archived": 0,
            "directories_deleted": 0,
            "files_deleted": 0,
            "errors": [],
            "dry_run": dry_run,
        }
        
        logger.info(f"[StorageManager] Nettoyage des fichiers antérieurs au {cutoff_date.date()}")
        
        # Parcourir les sources
        for source_dir in self.base_path.iterdir():
            if not source_dir.is_dir() or source_dir.name == "archive":
                continue
            
            # Parcourir les sous-répertoires (dates généralement)
            for subdir in source_dir.iterdir():
                if not subdir.is_dir():
                    continue
                
                # Vérifier si tous les fichiers du répertoire sont anciens
                all_old = True
                for file_path in subdir.rglob("*.md"):
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime >= cutoff_date:
                        all_old = False
                        break
                
                if all_old:
                    logger.info(f"[StorageManager] Répertoire à nettoyer: {subdir}")
                    
                    if not dry_run:
                        # Archiver puis supprimer
                        archive_result = self.archive_directory(subdir)
                        if archive_result:
                            stats["directories_archived"] += 1
                            try:
                                # Compter les fichiers avant suppression
                                file_count = len(list(subdir.rglob("*.md")))
                                shutil.rmtree(subdir)
                                stats["directories_deleted"] += 1
                                stats["files_deleted"] += file_count
                                logger.info(f"[StorageManager] Répertoire supprimé: {subdir}")
                            except Exception as e:
                                stats["errors"].append(f"Suppression de {subdir}: {e}")
                                logger.error(f"[StorageManager] Erreur lors de la suppression de {subdir}: {e}")
                        else:
                            stats["errors"].append(f"Archivage échoué pour {subdir}")
                    else:
                        stats["directories_archived"] += 1
                        stats["directories_deleted"] += 1
                        stats["files_deleted"] += len(list(subdir.rglob("*.md")))
        
        logger.info(f"[StorageManager] Nettoyage terminé: {stats}")
        return stats
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Retourne des statistiques sur le stockage.
        
        Returns:
            Dictionnaire avec les statistiques
        """
        stats = {
            "base_dir": str(self.base_path),
            "sources": {},
            "total_files": 0,
            "total_size_bytes": 0,
        }
        
        for source_dir in self.base_path.iterdir():
            if not source_dir.is_dir() or source_dir.name == "archive":
                continue
            
            source_stats = {
                "file_count": 0,
                "size_bytes": 0,
                "subdirs": [],
            }
            
            for file_path in source_dir.rglob("*.md"):
                source_stats["file_count"] += 1
                source_stats["size_bytes"] += file_path.stat().st_size
            
            for subdir in source_dir.iterdir():
                if subdir.is_dir():
                    source_stats["subdirs"].append(subdir.name)
            
            stats["sources"][source_dir.name] = source_stats
            stats["total_files"] += source_stats["file_count"]
            stats["total_size_bytes"] += source_stats["size_bytes"]
        
        return stats
