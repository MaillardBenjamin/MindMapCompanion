"""
Outils Agno pour le scraping d'offres d'emploi.

Ces outils permettent aux agents configurables d'utiliser le système de scraping
basé sur les configurations markdown Playwright.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from agno.tools import Toolkit, tool

from app.services.job_scraping.job_scraping_service import JobScrapingService, get_job_scraping_service
from app.services.job_scraping.storage_manager import StorageManager, StorageConfig
from app.services.email_smtp import EmailSMTPService

logger = logging.getLogger(__name__)


class JobScrapingTools(Toolkit):
    """
    Toolkit Agno pour le scraping d'offres d'emploi.
    
    Fournit des outils pour :
    - Scraper les offres depuis les sites configurés
    - Lire les offres sauvegardées
    - Envoyer des emails avec les résultats
    """
    
    def __init__(
        self,
        agent_config: Optional[Dict[str, Any]] = None,
        scraping_service: Optional[JobScrapingService] = None,
    ):
        """
        Initialise le toolkit.
        
        Args:
            agent_config: Configuration de l'agent (optionnel)
            scraping_service: Service de scraping (optionnel, sera créé si non fourni)
        """
        super().__init__(name="job_scraping_tools")
        
        self.agent_config = agent_config or {}
        self.scraping_service = scraping_service or get_job_scraping_service()
        
        # Configurer le storage depuis la config de l'agent
        self.storage_config = self.agent_config.get("storage", {})
        
        # Récupérer les scrapers configurés
        self.configured_scrapers = self.agent_config.get("scrapers", [])
        
        logger.info(f"[JobScrapingTools] Initialisé avec {len(self.configured_scrapers)} scrapers configurés")
    
    @tool(description="Scrape les offres d'emploi depuis les sites configurés (Cadre Emploi, Indeed, Welcome to the Jungle). Retourne les chemins des fichiers markdown sauvegardés.")
    def scrape_job_offers(
        self,
        keywords: str,
        location: str,
        sources: Optional[str] = None,
    ) -> str:
        """
        Scrape les offres d'emploi depuis les sites configurés.
        
        Args:
            keywords: Mots-clés de recherche (ex: "Développeur Python", "Data Engineer")
            location: Localisation souhaitée (ex: "Paris", "Lyon", "Remote")
            sources: Sources à utiliser, séparées par des virgules (optionnel, utilise toutes les sources configurées par défaut)
        
        Returns:
            Résumé du scraping avec les chemins des fichiers créés
        """
        search_params = {
            "keywords": keywords,
            "location": location,
        }
        
        # Déterminer les scrapers à utiliser
        scraper_paths = self.configured_scrapers
        if sources:
            source_list = [s.strip().lower() for s in sources.split(",")]
            scraper_paths = [
                s for s in scraper_paths
                if any(source in s.lower() for source in source_list)
            ]
        
        if not scraper_paths:
            # Utiliser les scrapers par défaut
            scraper_paths = [
                "scrapers/cadre-emploi-scraper.md",
                "scrapers/indeed-scraper.md",
                "scrapers/welcome-to-the-jungle-scraper.md",
            ]
        
        logger.info(f"[JobScrapingTools] Scraping avec {len(scraper_paths)} sources: {scraper_paths}")
        
        # Exécuter le scraping de manière synchrone (Agno tools sont synchrones)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        try:
            results = loop.run_until_complete(
                self.scraping_service.scrape_multiple(
                    config_paths=scraper_paths,
                    search_params=search_params,
                    save_to_files=True,
                )
            )
        except Exception as e:
            logger.error(f"[JobScrapingTools] Erreur lors du scraping: {e}", exc_info=True)
            return f"Erreur lors du scraping: {str(e)}"
        
        # Construire le résumé
        total_offers = 0
        all_files = []
        summary_parts = ["## Résultat du scraping\n"]
        
        for source, result in results.items():
            total_offers += result.offers_count
            all_files.extend([str(f) for f in result.saved_files])
            
            status = "✅" if result.success else "❌"
            summary_parts.append(f"- {status} **{source}**: {result.offers_count} offres")
            
            if result.errors:
                for error in result.errors:
                    summary_parts.append(f"  - ⚠️ {error}")
        
        summary_parts.append(f"\n**Total**: {total_offers} offres extraites")
        summary_parts.append(f"**Fichiers créés**: {len(all_files)}")
        
        if all_files[:5]:
            summary_parts.append("\n### Exemples de fichiers:")
            for f in all_files[:5]:
                summary_parts.append(f"- `{f}`")
        
        return "\n".join(summary_parts)
    
    @tool(description="Liste les offres d'emploi sauvegardées en markdown. Peut filtrer par source et date.")
    def list_saved_offers(
        self,
        source: Optional[str] = None,
        days: int = 7,
    ) -> str:
        """
        Liste les offres d'emploi sauvegardées.
        
        Args:
            source: Filtrer par source (cadre-emploi, indeed, welcome-to-the-jungle)
            days: Nombre de jours à considérer (défaut: 7)
        
        Returns:
            Liste des offres avec leurs métadonnées
        """
        from datetime import datetime, timedelta
        
        # Créer un StorageManager pour lire les fichiers
        storage_config = StorageConfig.from_dict(self.storage_config)
        project_root = Path(__file__).parent.parent.parent
        storage_manager = StorageManager(storage_config, project_root)
        
        since = datetime.now() - timedelta(days=days)
        files = storage_manager.list_offers(source=source, since=since)
        
        if not files:
            return f"Aucune offre trouvée pour les {days} derniers jours."
        
        summary_parts = [f"## {len(files)} offres trouvées\n"]
        
        for file_path in files[:20]:  # Limiter à 20 résultats
            offer = storage_manager.read_offer(file_path)
            if offer:
                frontmatter = offer.get("frontmatter", {})
                title = frontmatter.get("title", file_path.stem)
                company = frontmatter.get("company", "N/A")
                source_name = frontmatter.get("source", "unknown")
                
                summary_parts.append(f"- **{title}** @ {company} ({source_name})")
                summary_parts.append(f"  - Fichier: `{file_path}`")
        
        if len(files) > 20:
            summary_parts.append(f"\n... et {len(files) - 20} autres offres")
        
        return "\n".join(summary_parts)
    
    @tool(description="Lit le contenu complet d'une offre d'emploi depuis son fichier markdown.")
    def read_offer_content(self, file_path: str) -> str:
        """
        Lit le contenu d'une offre d'emploi.
        
        Args:
            file_path: Chemin du fichier markdown de l'offre
        
        Returns:
            Contenu complet de l'offre en markdown
        """
        try:
            path = Path(file_path)
            if not path.is_absolute():
                project_root = Path(__file__).parent.parent.parent
                path = project_root / file_path
            
            if not path.exists():
                return f"Fichier non trouvé: {file_path}"
            
            return path.read_text(encoding="utf-8")
        except Exception as e:
            return f"Erreur lors de la lecture: {str(e)}"
    
    @tool(description="Envoie un email avec les résultats du matching d'offres d'emploi.")
    def send_job_matching_email(
        self,
        recipient: str,
        subject: str,
        body: str,
    ) -> str:
        """
        Envoie un email avec les résultats du matching.
        
        Args:
            recipient: Adresse email du destinataire
            subject: Sujet de l'email
            body: Contenu de l'email (supporte le markdown)
        
        Returns:
            Statut de l'envoi
        """
        try:
            email_service = EmailSMTPService()
            
            # Convertir le markdown en HTML basique
            html_body = self._markdown_to_html(body)
            
            success = email_service.send_email(
                to_email=recipient,
                subject=subject,
                text_content=body,
                html_content=html_body,
            )
            
            if success:
                return f"✅ Email envoyé avec succès à {recipient}"
            else:
                return f"❌ Échec de l'envoi de l'email à {recipient}"
                
        except Exception as e:
            logger.error(f"[JobScrapingTools] Erreur envoi email: {e}", exc_info=True)
            return f"❌ Erreur lors de l'envoi: {str(e)}"
    
    @tool(description="Retourne les statistiques de stockage des offres d'emploi.")
    def get_storage_stats(self) -> str:
        """
        Retourne les statistiques de stockage.
        
        Returns:
            Statistiques sur les offres sauvegardées
        """
        storage_config = StorageConfig.from_dict(self.storage_config)
        project_root = Path(__file__).parent.parent.parent
        storage_manager = StorageManager(storage_config, project_root)
        
        stats = storage_manager.get_storage_stats()
        
        summary_parts = ["## Statistiques de stockage\n"]
        summary_parts.append(f"**Répertoire**: `{stats['base_dir']}`")
        summary_parts.append(f"**Total fichiers**: {stats['total_files']}")
        summary_parts.append(f"**Taille totale**: {stats['total_size_bytes'] / 1024:.1f} KB")
        
        if stats["sources"]:
            summary_parts.append("\n### Par source:")
            for source, source_stats in stats["sources"].items():
                summary_parts.append(f"- **{source}**: {source_stats['file_count']} fichiers ({source_stats['size_bytes'] / 1024:.1f} KB)")
        
        return "\n".join(summary_parts)
    
    @tool(description="Liste les scrapers disponibles avec leurs configurations.")
    def list_available_scrapers(self) -> str:
        """
        Liste les scrapers disponibles.
        
        Returns:
            Liste des scrapers avec leurs informations
        """
        scrapers = self.scraping_service.list_available_scrapers()
        
        if not scrapers:
            return "Aucun scraper configuré trouvé."
        
        summary_parts = [f"## {len(scrapers)} scrapers disponibles\n"]
        
        for scraper in scrapers:
            auth_required = "🔐" if scraper.get("requires_auth") else "🔓"
            summary_parts.append(f"- {auth_required} **{scraper['name']}**")
            summary_parts.append(f"  - URL: {scraper['site_url']}")
            summary_parts.append(f"  - Chemin: `{scraper['path']}`")
            summary_parts.append(f"  - Étapes: {scraper['steps_count']}")
        
        return "\n".join(summary_parts)
    
    def _markdown_to_html(self, markdown_text: str) -> str:
        """Convertit du markdown basique en HTML"""
        import re
        
        html = markdown_text
        
        # Headers
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        
        # Bold
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        
        # Italic
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        
        # Code
        html = re.sub(r'`(.+?)`', r'<code>\1</code>', html)
        
        # Lists
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        
        # Links
        html = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', html)
        
        # Paragraphs
        html = re.sub(r'\n\n', '</p><p>', html)
        html = f'<p>{html}</p>'
        
        return html


def get_job_scraping_toolkit(agent_config: Optional[Dict[str, Any]] = None) -> JobScrapingTools:
    """
    Crée une instance du toolkit de scraping.
    
    Args:
        agent_config: Configuration de l'agent (optionnel)
    
    Returns:
        Instance du toolkit
    """
    return JobScrapingTools(agent_config=agent_config)
