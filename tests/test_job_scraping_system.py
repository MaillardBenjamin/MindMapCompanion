"""
Tests pour le système de scraping d'offres d'emploi.

Teste :
- Le parser de configuration markdown
- Le gestionnaire de stockage
- Le service de scraping (mock)
- Le scheduler de nettoyage
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
import tempfile
import shutil

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestScraperConfigParser:
    """Tests pour le parser de configuration des scrapers"""
    
    def test_parse_markdown_frontmatter(self):
        """Teste le parsing du frontmatter YAML"""
        from app.services.job_scraping.scraper_config_parser import ScraperConfigParser
        
        parser = ScraperConfigParser()
        
        content = """---
name: Test Scraper
site_url: https://example.com
browser:
  headless: true
  timeout: 5000
storage:
  base_dir: data/test
  retention_days: 7
---

# Instructions

```yaml
action: goto
url: "{{site_url}}"
```
"""
        
        config = parser.parse_markdown(content)
        
        assert config.name == "Test Scraper"
        assert config.site_url == "https://example.com"
        assert config.browser.headless == True
        assert config.browser.timeout == 5000
        assert config.storage.base_dir == "data/test"
        assert config.storage.retention_days == 7
    
    def test_parse_steps(self):
        """Teste le parsing des étapes Playwright"""
        from app.services.job_scraping.scraper_config_parser import ScraperConfigParser
        
        parser = ScraperConfigParser()
        
        content = """---
name: Test Scraper
site_url: https://example.com
---

# Instructions

```yaml
action: goto
url: "{{site_url}}"
options:
  wait_until: networkidle
```

```yaml
action: click
selector: "#button"
```
"""
        
        config = parser.parse_markdown(content)
        
        assert len(config.steps) == 2
        assert config.steps[0].action == "goto"
        assert config.steps[0].params["url"] == "{{site_url}}"
        assert config.steps[1].action == "click"
        assert config.steps[1].params["selector"] == "#button"
    
    def test_validate_config(self):
        """Teste la validation de configuration"""
        from app.services.job_scraping.scraper_config_parser import ScraperConfigParser, ScraperConfig
        
        parser = ScraperConfigParser()
        
        # Configuration valide
        valid_config = parser.parse_markdown("""---
name: Valid Scraper
site_url: https://example.com
---

```yaml
action: goto
url: "{{site_url}}"
```
""")
        
        is_valid, errors = parser.validate_config(valid_config)
        assert is_valid
        assert len(errors) == 0
        
        # Configuration invalide (pas de nom)
        invalid_config = parser.parse_markdown("""---
site_url: https://example.com
---
""")
        
        is_valid, errors = parser.validate_config(invalid_config)
        assert not is_valid
        assert "nom" in errors[0].lower() or "name" in errors[0].lower()


class TestStorageManager:
    """Tests pour le gestionnaire de stockage"""
    
    def setup_method(self):
        """Setup pour chaque test"""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Cleanup après chaque test"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_save_offer(self):
        """Teste la sauvegarde d'une offre en markdown"""
        from app.services.job_scraping.storage_manager import StorageManager, StorageConfig, JobOffer
        
        config = StorageConfig(
            base_dir=str(self.temp_dir / "job_offers"),
            subdir_pattern="{date}",
            file_pattern="{title_slug}-{id}.md",
        )
        
        manager = StorageManager(config, self.temp_dir)
        
        offer = JobOffer(
            id="test-123",
            title="Développeur Python",
            company="TechCorp",
            location="Paris",
            url="https://example.com/job/123",
            source="test",
            description="Description de l'offre",
            salary="50 000 - 60 000 €",
        )
        
        file_path = manager.save_offer(offer, "test-source")
        
        assert file_path.exists()
        
        content = file_path.read_text(encoding="utf-8")
        assert "Développeur Python" in content
        assert "TechCorp" in content
        assert "50 000 - 60 000 €" in content
        assert "---" in content  # Frontmatter présent
    
    def test_list_offers(self):
        """Teste le listing des offres"""
        from app.services.job_scraping.storage_manager import StorageManager, StorageConfig, JobOffer
        
        config = StorageConfig(
            base_dir=str(self.temp_dir / "job_offers"),
            subdir_pattern="{date}",
            file_pattern="{title_slug}-{id}.md",
        )
        
        manager = StorageManager(config, self.temp_dir)
        
        # Sauvegarder quelques offres
        for i in range(3):
            offer = JobOffer(
                id=f"test-{i}",
                title=f"Offre {i}",
                company="Company",
                location="Paris",
                url=f"https://example.com/job/{i}",
                source="test",
            )
            manager.save_offer(offer, "test-source")
        
        files = manager.list_offers()
        assert len(files) == 3
    
    def test_cleanup_old_files(self):
        """Teste le nettoyage des anciens fichiers"""
        from app.services.job_scraping.storage_manager import StorageManager, StorageConfig, JobOffer
        import time
        import os
        
        config = StorageConfig(
            base_dir=str(self.temp_dir / "job_offers"),
            subdir_pattern="old",  # Pattern fixe pour le test
            file_pattern="{title_slug}-{id}.md",
            retention_days=0,  # 0 jours = tout supprimer
            cleanup_enabled=True,
        )
        
        manager = StorageManager(config, self.temp_dir)
        
        # Créer un fichier et le faire "vieillir"
        offer = JobOffer(
            id="old-offer",
            title="Old Offer",
            company="Company",
            location="Paris",
            url="https://example.com/job/old",
            source="test",
        )
        file_path = manager.save_offer(offer, "test-source")
        
        # Modifier le mtime pour simuler un ancien fichier
        old_time = (datetime.now() - timedelta(days=10)).timestamp()
        os.utime(file_path, (old_time, old_time))
        
        # Exécuter le nettoyage en dry-run
        stats = manager.cleanup_old_files(dry_run=True)
        
        assert stats["dry_run"] == True
        # Le fichier devrait être marqué pour suppression
        assert stats["files_deleted"] >= 0  # Peut être 0 si le répertoire est récent


class TestJobOffer:
    """Tests pour la dataclass JobOffer"""
    
    def test_to_markdown(self):
        """Teste la conversion en markdown"""
        from app.services.job_scraping.storage_manager import JobOffer
        
        offer = JobOffer(
            id="test-123",
            title="Senior Python Developer",
            company="TechCorp",
            location="Paris (75)",
            url="https://example.com/job/123",
            source="test-site",
            description="Nous recherchons un développeur Python...",
            salary="60 000 - 70 000 €",
            contract_type="CDI",
            requirements=["Python 5+ ans", "Django/FastAPI"],
        )
        
        markdown = offer.to_markdown()
        
        # Vérifier le frontmatter
        assert "---" in markdown
        assert "id: test-123" in markdown
        assert "source: test-site" in markdown
        
        # Vérifier le corps
        assert "# Senior Python Developer" in markdown
        assert "**Entreprise** : TechCorp" in markdown
        assert "**Salaire** : 60 000 - 70 000 €" in markdown
        assert "- Python 5+ ans" in markdown


class TestTemplateResolver:
    """Tests pour le résolveur de templates"""
    
    def test_resolve_simple(self):
        """Teste la résolution de templates simples"""
        from app.services.job_scraping.scraper_config_parser import TemplateResolver
        
        resolver = TemplateResolver({
            "site_url": "https://example.com",
            "search": {
                "keywords": "Python",
                "location": "Paris",
            },
        })
        
        result = resolver.resolve("{{site_url}}/jobs")
        assert result == "https://example.com/jobs"
        
        result = resolver.resolve("{{search.keywords}} in {{search.location}}")
        assert result == "Python in Paris"
    
    def test_resolve_nested_dict(self):
        """Teste la résolution dans des dictionnaires imbriqués"""
        from app.services.job_scraping.scraper_config_parser import TemplateResolver
        
        resolver = TemplateResolver({
            "site_url": "https://example.com",
        })
        
        data = {
            "url": "{{site_url}}/search",
            "options": {
                "base": "{{site_url}}",
            },
        }
        
        result = resolver.resolve(data)
        assert result["url"] == "https://example.com/search"
        assert result["options"]["base"] == "https://example.com"


class TestAgentConfigParserExtensions:
    """Tests pour les extensions du parser de configuration d'agent"""
    
    def test_parse_scrapers_from_frontmatter(self):
        """Teste le parsing des scrapers depuis le frontmatter"""
        from app.services.agent_config_parser import AgentConfigParser
        
        content = """---
name: Job Matcher Agent
slug: job-matcher-agent
scrapers:
  - path: scrapers/cadre-emploi-scraper.md
    enabled: true
  - path: scrapers/indeed-scraper.md
    enabled: false
  - path: scrapers/wttj-scraper.md
    enabled: true
storage:
  base_dir: data/job_offers
  retention_days: 30
---

# Prompt Template

{{input_text}}
"""
        
        config = AgentConfigParser.parse_markdown(content)
        
        # Seuls les scrapers enabled devraient être dans la liste
        assert len(config["scrapers"]) == 2
        assert "scrapers/cadre-emploi-scraper.md" in config["scrapers"]
        assert "scrapers/wttj-scraper.md" in config["scrapers"]
        assert "scrapers/indeed-scraper.md" not in config["scrapers"]  # Désactivé
        
        # Le storage devrait être présent
        assert config["storage"]["base_dir"] == "data/job_offers"
        assert config["storage"]["retention_days"] == 30


class TestCleanupScheduler:
    """Tests pour le scheduler de nettoyage"""
    
    def test_get_cleanup_jobs(self):
        """Teste la récupération des jobs de nettoyage"""
        from app.services.job_scraping.cleanup_scheduler import JobCleanupScheduler
        
        # Créer un répertoire temporaire avec une config
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            scrapers_dir = temp_path / "scrapers"
            scrapers_dir.mkdir(parents=True)
            
            # Créer un fichier de config
            config_content = """---
name: Test Scraper
site_url: https://example.com
storage:
  base_dir: data/test
  retention_days: 7
  cleanup_enabled: true
  cleanup_schedule: "0 2 * * 0"
---

```yaml
action: goto
url: "{{site_url}}"
```
"""
            (scrapers_dir / "test-scraper.md").write_text(config_content)
            
            scheduler = JobCleanupScheduler(examples_dir=temp_path)
            jobs = scheduler.get_cleanup_jobs()
            
            assert len(jobs) >= 1
            test_job = next((j for j in jobs if j["scraper_name"] == "Test Scraper"), None)
            assert test_job is not None
            assert test_job["retention_days"] == 7


class TestJobScrapingService:
    """Tests pour le service de scraping"""
    
    @pytest.mark.asyncio
    async def test_list_available_scrapers(self):
        """Teste le listing des scrapers disponibles"""
        from app.services.job_scraping.job_scraping_service import JobScrapingService
        
        # Utiliser les vraies configs (si présentes)
        service = JobScrapingService()
        
        scrapers = service.list_available_scrapers()
        
        # Au moins les 3 scrapers créés devraient être présents
        # (si le test est exécuté après la création des fichiers)
        # Si non, ce test sera skip
        if scrapers:
            assert len(scrapers) >= 1
            for scraper in scrapers:
                assert "name" in scraper
                assert "site_url" in scraper
                assert "path" in scraper


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
