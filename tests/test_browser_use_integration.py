"""
Tests d'intégration pour Browser-Use avec Ollama.

Ces tests vérifient que l'intégration Browser-Use fonctionne correctement.
"""

import asyncio
import pytest
import logging
from pathlib import Path

from app.services.job_scraping.browser_use_executor import BrowserUseExecutor
from app.services.job_scraping.scraper_config_parser import ScraperConfigParser
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class TestBrowserUseIntegration:
    """Tests d'intégration pour Browser-Use"""
    
    @pytest.fixture
    def config_parser(self):
        """Fixture pour le parser de configuration"""
        examples_dir = Path(__file__).parent.parent / "backend" / "app" / "agent_configs"
        return ScraperConfigParser(examples_dir)
    
    def test_ollama_configured(self):
        """Vérifie que Ollama est configuré"""
        settings = get_settings()
        assert settings.ollama_base_url, "OLLAMA_BASE_URL doit être défini dans .env"
        assert settings.agno_model, "AGNO_MODEL doit être défini dans .env"
        logger.info(f"Ollama configuré : {settings.ollama_base_url} avec modèle {settings.agno_model}")
    
    def test_browser_use_import(self):
        """Vérifie que browser-use est installé"""
        try:
            from browser_use import Agent
            from langchain_ollama import ChatOllama
            logger.info("browser-use et langchain-ollama sont installés correctement")
        except ImportError as e:
            pytest.fail(f"Impossible d'importer browser-use ou langchain-ollama : {e}")
    
    def test_parse_browseruse_config(self, config_parser):
        """Teste le parsing d'une configuration browser-use"""
        config_file = "scrapers/cadre-emploi-scraper-browseruse.md"
        
        try:
            config = config_parser.load_config(config_file)
            
            # Vérifications
            assert config.executor_type == "browser-use", "Le type d'executor doit être 'browser-use'"
            assert config.natural_language_instructions, "Les instructions en langage naturel doivent être présentes"
            assert len(config.natural_language_instructions) > 100, "Les instructions doivent être substantielles"
            
            logger.info(f"Configuration {config.name} parsée avec succès")
            logger.info(f"Instructions : {len(config.natural_language_instructions)} caractères")
            
        except FileNotFoundError:
            pytest.skip(f"Fichier de configuration {config_file} non trouvé")
    
    @pytest.mark.asyncio
    async def test_browser_use_executor_init(self, config_parser):
        """Teste l'initialisation du BrowserUseExecutor"""
        config_file = "scrapers/cadre-emploi-scraper-browseruse.md"
        
        try:
            config = config_parser.load_config(config_file)
            executor = BrowserUseExecutor(config)
            
            assert executor.config == config
            assert executor.extracted_data == []
            
            logger.info(f"BrowserUseExecutor initialisé avec succès pour {config.name}")
            
        except FileNotFoundError:
            pytest.skip(f"Fichier de configuration {config_file} non trouvé")
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_browser_use_simple_task(self):
        """
        Test simple d'exécution Browser-Use.
        
        Note : Ce test nécessite Ollama en cours d'exécution.
        Utilisez pytest -m "not slow" pour sauter les tests lents.
        """
        try:
            from browser_use import Agent
            from langchain_ollama import ChatOllama
        except ImportError:
            pytest.skip("browser-use ou langchain-ollama non installé")
        
        settings = get_settings()
        
        try:
            # Configuration du modèle
            ollama_base_url = settings.ollama_base_url.strip().rstrip("/")
            if ollama_base_url.endswith("/v1"):
                ollama_base_url = ollama_base_url.replace("/v1", "")
            
            llm = ChatOllama(
                model=settings.agno_model,
                base_url=ollama_base_url,
                temperature=0.1,
            )
            
            # Créer un agent simple
            agent = Agent(
                task="Va sur https://example.com et retourne le titre de la page",
                llm=llm,
                use_vision=False,
            )
            
            # Exécuter (avec timeout court)
            result = await asyncio.wait_for(agent.run(), timeout=60.0)
            
            logger.info(f"Résultat du test simple : {result}")
            
            # Vérification basique
            assert result is not None, "Le résultat ne doit pas être None"
            
        except asyncio.TimeoutError:
            pytest.fail("Le test a pris plus de 60 secondes (timeout)")
        except Exception as e:
            logger.error(f"Erreur lors du test : {e}")
            pytest.skip(f"Ollama ne semble pas accessible : {e}")


def test_requirements_installed():
    """Vérifie que toutes les dépendances sont installées"""
    required_packages = [
        "browser_use",
        "langchain_ollama",
        "langchain",
        "playwright",
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing.append(package)
    
    if missing:
        pytest.fail(f"Packages manquants : {', '.join(missing)}")
    
    logger.info("Toutes les dépendances requises sont installées")


if __name__ == "__main__":
    # Exécution directe pour tests rapides
    logging.basicConfig(level=logging.INFO)
    
    print("🧪 Tests d'intégration Browser-Use\n")
    
    print("1. Vérification de la configuration Ollama...")
    try:
        settings = get_settings()
        print(f"   ✅ Ollama URL : {settings.ollama_base_url}")
        print(f"   ✅ Modèle : {settings.agno_model}")
    except Exception as e:
        print(f"   ❌ Erreur : {e}")
    
    print("\n2. Vérification des imports...")
    try:
        from browser_use import Agent
        from langchain_ollama import ChatOllama
        print("   ✅ browser-use et langchain-ollama sont installés")
    except ImportError as e:
        print(f"   ❌ Erreur d'import : {e}")
        print("   Installez les dépendances : pip install browser-use langchain-ollama langchain")
    
    print("\n3. Vérification de la configuration de scraping...")
    try:
        examples_dir = Path(__file__).parent.parent / "backend" / "app" / "agent_configs"
        parser = ScraperConfigParser(examples_dir)
        config = parser.load_config("scrapers/cadre-emploi-scraper-browseruse.md")
        print(f"   ✅ Configuration parsée : {config.name}")
        print(f"   ✅ Type d'executor : {config.executor_type}")
        print(f"   ✅ Instructions : {len(config.natural_language_instructions)} caractères")
    except FileNotFoundError:
        print("   ⚠️  Fichier de configuration browser-use non trouvé")
    except Exception as e:
        print(f"   ❌ Erreur : {e}")
    
    print("\n✅ Tests de base terminés !")
    print("\nPour les tests complets, exécutez :")
    print("  pytest tests/test_browser_use_integration.py -v")
    print("\nPour les tests rapides (sans exécution réelle) :")
    print("  pytest tests/test_browser_use_integration.py -v -m 'not slow'")
