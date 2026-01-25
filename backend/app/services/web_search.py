"""
Service de recherche web utilisant Google Search API et Bing Search API.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class WebSearchResult:
    """Résultat d'une recherche web"""
    def __init__(
        self,
        title: str,
        url: str,
        snippet: str,
        source: Optional[str] = None,
        date: Optional[str] = None,
    ):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.source = source
        self.date = date
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "date": self.date,
        }


class WebSearchService:
    """Service de recherche web avec support Google et Bing"""
    
    def __init__(self, provider: str = "google"):
        """
        Initialise le service de recherche web.
        
        Args:
            provider: "google" ou "bing"
        """
        self.provider = provider.lower()
        self.google_api_key = None
        self.google_engine_id = None
        self.bing_api_key = None
    
    def configure_google(self, api_key: str, engine_id: str):
        """Configure l'API Google Search"""
        self.google_api_key = api_key
        self.google_engine_id = engine_id
    
    def configure_bing(self, api_key: str):
        """Configure l'API Bing Search"""
        self.bing_api_key = api_key
    
    def search(
        self,
        query: str,
        num_results: int = 10,
        language: str = "fr",
        region: Optional[str] = None,
    ) -> List[WebSearchResult]:
        """
        Effectue une recherche web.
        
        Args:
            query: Terme de recherche
            num_results: Nombre de résultats à retourner (max 10 pour Google, 50 pour Bing)
            language: Code langue (fr, en, etc.)
            region: Code région (optionnel)
        
        Returns:
            Liste de résultats de recherche
        """
        if self.provider == "google":
            return self._search_google(query, num_results, language, region)
        elif self.provider == "bing":
            return self._search_bing(query, num_results, language, region)
        else:
            raise ValueError(f"Provider non supporté: {self.provider}")
    
    def _search_google(
        self,
        query: str,
        num_results: int = 10,
        language: str = "fr",
        region: Optional[str] = None,
    ) -> List[WebSearchResult]:
        """Recherche via Google Custom Search API"""
        if not self.google_api_key or not self.google_engine_id:
            logger.warning("Google Search API non configurée, utilisation d'une recherche simulée")
            return self._mock_search(query, num_results)
        
        try:
            from serpapi import GoogleSearch
            
            params = {
                "q": query,
                "api_key": self.google_api_key,
                "engine": "google",
                "num": min(num_results, 10),  # Google limite à 10 résultats par requête
                "hl": language,
            }
            
            if self.google_engine_id:
                params["cx"] = self.google_engine_id
            
            if region:
                params["gl"] = region
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            search_results = []
            if "organic_results" in results:
                for item in results["organic_results"][:num_results]:
                    search_results.append(WebSearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                        source=item.get("source", ""),
                        date=item.get("date", None),
                    ))
            
            logger.info(f"Recherche Google: {len(search_results)} résultats pour '{query}'")
            return search_results
            
        except ImportError:
            logger.warning("serpapi non installé, utilisation d'une recherche simulée")
            return self._mock_search(query, num_results)
        except Exception as e:
            logger.error(f"Erreur lors de la recherche Google: {e}")
            return self._mock_search(query, num_results)
    
    def _search_bing(
        self,
        query: str,
        num_results: int = 10,
        language: str = "fr",
        region: Optional[str] = None,
    ) -> List[WebSearchResult]:
        """Recherche via Bing Search API"""
        if not self.bing_api_key:
            logger.warning("Bing Search API non configurée, utilisation d'une recherche simulée")
            return self._mock_search(query, num_results)
        
        try:
            import requests
            
            endpoint = "https://api.bing.microsoft.com/v7.0/search"
            headers = {
                "Ocp-Apim-Subscription-Key": self.bing_api_key,
            }
            params = {
                "q": query,
                "count": min(num_results, 50),  # Bing limite à 50 résultats
                "mkt": f"{language}-{region or 'FR'}" if region else language,
                "textDecorations": True,
                "textFormat": "HTML",
            }
            
            response = requests.get(endpoint, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            search_results = []
            if "webPages" in data and "value" in data["webPages"]:
                for item in data["webPages"]["value"][:num_results]:
                    search_results.append(WebSearchResult(
                        title=item.get("name", ""),
                        url=item.get("url", ""),
                        snippet=item.get("snippet", ""),
                        source=item.get("displayUrl", ""),
                        date=item.get("dateLastCrawled", None),
                    ))
            
            logger.info(f"Recherche Bing: {len(search_results)} résultats pour '{query}'")
            return search_results
            
        except ImportError:
            logger.warning("requests non installé, utilisation d'une recherche simulée")
            return self._mock_search(query, num_results)
        except Exception as e:
            logger.error(f"Erreur lors de la recherche Bing: {e}")
            return self._mock_search(query, num_results)
    
    def _mock_search(self, query: str, num_results: int) -> List[WebSearchResult]:
        """Recherche simulée pour les tests (sans API)"""
        logger.info(f"Recherche simulée pour '{query}' ({num_results} résultats)")
        # Retourner des résultats factices pour les tests
        return [
            WebSearchResult(
                title=f"Résultat {i+1} pour '{query}'",
                url=f"https://example.com/result-{i+1}",
                snippet=f"Ceci est un résultat simulé pour la recherche '{query}'. Configurez une API de recherche réelle pour obtenir de vrais résultats.",
                source="example.com",
                date=datetime.now().isoformat(),
            )
            for i in range(min(num_results, 5))
        ]
    
    def search_news(
        self,
        query: str,
        num_results: int = 10,
        language: str = "fr",
    ) -> List[WebSearchResult]:
        """
        Recherche d'actualités récentes.
        
        Args:
            query: Terme de recherche
            num_results: Nombre de résultats
            language: Code langue
        
        Returns:
            Liste de résultats d'actualités
        """
        if self.provider == "google":
            return self._search_google_news(query, num_results, language)
        elif self.provider == "bing":
            return self._search_bing_news(query, num_results, language)
        else:
            return self._mock_search(query, num_results)
    
    def _search_google_news(
        self,
        query: str,
        num_results: int = 10,
        language: str = "fr",
    ) -> List[WebSearchResult]:
        """Recherche d'actualités via Google News"""
        if not self.google_api_key:
            return self._mock_search(query, num_results)
        
        try:
            from serpapi import GoogleSearch
            
            params = {
                "q": query,
                "api_key": self.google_api_key,
                "engine": "google_news",
                "num": min(num_results, 10),
                "hl": language,
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            search_results = []
            if "news_results" in results:
                for item in results["news_results"][:num_results]:
                    search_results.append(WebSearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                        source=item.get("source", ""),
                        date=item.get("date", None),
                    ))
            
            return search_results
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche Google News: {e}")
            return self._mock_search(query, num_results)
    
    def _search_bing_news(
        self,
        query: str,
        num_results: int = 10,
        language: str = "fr",
    ) -> List[WebSearchResult]:
        """Recherche d'actualités via Bing News"""
        if not self.bing_api_key:
            return self._mock_search(query, num_results)
        
        try:
            import requests
            
            endpoint = "https://api.bing.microsoft.com/v7.0/news/search"
            headers = {
                "Ocp-Apim-Subscription-Key": self.bing_api_key,
            }
            params = {
                "q": query,
                "count": min(num_results, 50),
                "mkt": language,
            }
            
            response = requests.get(endpoint, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            search_results = []
            if "value" in data:
                for item in data["value"][:num_results]:
                    search_results.append(WebSearchResult(
                        title=item.get("name", ""),
                        url=item.get("url", ""),
                        snippet=item.get("description", ""),
                        source=item.get("provider", [{}])[0].get("name", "") if item.get("provider") else "",
                        date=item.get("datePublished", None),
                    ))
            
            return search_results
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche Bing News: {e}")
            return self._mock_search(query, num_results)


# Instance singleton
_web_search_service: Optional[WebSearchService] = None


def get_web_search_service() -> WebSearchService:
    """Obtient l'instance singleton du service de recherche web"""
    global _web_search_service
    if _web_search_service is None:
        from app.core.config import get_settings
        settings = get_settings()
        
        _web_search_service = WebSearchService(provider=settings.search_provider)
        
        if settings.google_search_api_key and settings.google_search_engine_id:
            _web_search_service.configure_google(
                settings.google_search_api_key,
                settings.google_search_engine_id
            )
        
        if settings.bing_search_api_key:
            _web_search_service.configure_bing(settings.bing_search_api_key)
    
    return _web_search_service
