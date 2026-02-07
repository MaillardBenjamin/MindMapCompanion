"""
Service pour charger et exécuter les agents configurables.
"""

import json
import logging
import re
from urllib.parse import quote_plus
import time
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from agno.agent import Agent

# Uniquement Cadre Emploi pour l'instant.
DEFAULT_SCRAPER_PATHS = [
    "scrapers/cadre-emploi-scraper.md",
]
from app.core.agno_model import get_agno_chat_model
from app.core.config import get_settings
from app.models.configurable_agent import ConfigurableAgent, AgentExecutionLog
from app.services.agent_config_parser import AgentConfigParser

logger = logging.getLogger(__name__)


def _schema_to_markdown_description(schema: Dict[str, Any], indent: int = 0) -> str:
    """
    Convertit un schéma JSON en description textuelle Markdown.
    Cette description sert de référence structurelle sans inclure tout le JSON.
    """
    lines = []
    indent_str = "  " * indent
    
    if schema.get("type") == "object":
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        
        for prop_name, prop_schema in properties.items():
            is_required = prop_name in required
            req_marker = " (requis)" if is_required else " (optionnel)"
            
            prop_type = prop_schema.get("type", "string")
            description = prop_schema.get("description", "")
            
            if prop_type == "array":
                items = prop_schema.get("items", {})
                if items.get("type") == "object":
                    lines.append(f"{indent_str}- **{prop_name}**{req_marker}: Liste d'objets avec les propriétés suivantes:")
                    if description:
                        lines.append(f"{indent_str}  - {description}")
                    lines.append(_schema_to_markdown_description(items, indent + 1))
                else:
                    item_type = items.get("type", "string")
                    lines.append(f"{indent_str}- **{prop_name}**{req_marker}: Liste de {item_type}s")
                    if description:
                        lines.append(f"{indent_str}  - {description}")
            elif prop_type == "object":
                lines.append(f"{indent_str}- **{prop_name}**{req_marker}: Objet avec les propriétés suivantes:")
                if description:
                    lines.append(f"{indent_str}  - {description}")
                lines.append(_schema_to_markdown_description(prop_schema, indent + 1))
            else:
                enum_values = prop_schema.get("enum")
                if enum_values:
                    enum_str = ", ".join([f"`{v}`" for v in enum_values])
                    lines.append(f"{indent_str}- **{prop_name}**{req_marker}: {prop_type} - Valeurs possibles: {enum_str}")
                else:
                    lines.append(f"{indent_str}- **{prop_name}**{req_marker}: {prop_type}")
                if description:
                    lines.append(f"{indent_str}  - {description}")
    
    return "\n".join(lines)


class ConfigurableAgentService:
    """
    Service pour gérer et exécuter les agents IA configurables.
    
    Ce service permet de :
    - Créer des agents Agno depuis une configuration Markdown
    - Exécuter des agents avec des inputs personnalisés
    - Parser les sorties Markdown selon un schéma JSON
    - Logger toutes les exécutions pour traçabilité
    
    Les agents sont configurés via des fichiers Markdown avec :
    - Un persona (rôle de l'agent)
    - Des instructions détaillées
    - Un schéma de sortie JSON
    - Des outils disponibles (web_search, etc.)
    
    Example:
        >>> service = ConfigurableAgentService()
        >>> result = service.execute_agent(
        ...     db=session,
        ...     agent_id=1,
        ...     user_id=1,
        ...     input_text="Recherche actualités IA"
        ... )
    """
    
    def __init__(self):
        """
        Initialise le service avec les settings et le parser de configuration.
        """
        self.settings = get_settings()
        self.parser = AgentConfigParser()

    def _scraper_paths_from_markdown(self, markdown_config: Optional[str]) -> List[str]:
        """Extrait les chemins des scrapers depuis le frontmatter du markdown (pas config.tools).
        Limité à Cadre Emploi uniquement pour l'instant."""
        if not markdown_config:
            return list(DEFAULT_SCRAPER_PATHS)
        try:
            parsed = self.parser.parse_markdown(markdown_config)
            raw = parsed.get("scrapers") or []
            paths = []
            for p in raw:
                if isinstance(p, str) and p.strip():
                    path = p.strip()
                elif isinstance(p, dict) and p.get("enabled", True):
                    path = (p.get("path") or "").strip()
                else:
                    continue
                if path and "cadre-emploi" in path:
                    paths.append(path)
            if paths:
                logger.info("[ConfigurableAgent] 📂 Scrapers (Cadre Emploi uniquement): %s", paths)
                return paths
        except Exception as e:
            logger.warning("[ConfigurableAgent] Impossible d'extraire scrapers du markdown: %s", e)
        return list(DEFAULT_SCRAPER_PATHS)
    
    def _create_agent(self, config: ConfigurableAgent) -> Agent:
        """
        Crée un agent Agno depuis la configuration.
        
        Construit un agent Agno avec :
        - Le modèle OpenAI configuré
        - Les instructions (persona + instructions + schéma de sortie)
        - Les outils disponibles (DuckDuckGo pour recherche web)
        
        Args:
            config: Configuration de l'agent (ConfigurableAgent).
        
        Returns:
            Agent: Instance Agno configurée et prête à l'emploi.
        
        Note:
            Les outils de recherche web (DuckDuckGo) sont automatiquement
            ajoutés si demandés dans config.tools.
        """
        model = get_agno_chat_model()
        
        # Construire les instructions
        instructions_parts = []
        if config.persona:
            instructions_parts.append(f"Persona: {config.persona}")
        if config.instructions:
            instructions_parts.append(f"Instructions: {config.instructions}")
        if config.output_schema:
            # Convertir le schéma JSON en description textuelle Markdown
            schema_description = _schema_to_markdown_description(config.output_schema)
            instructions_parts.append(
                "## Structure de sortie attendue (format Markdown)\n\n"
                "Tu dois structurer ta réponse en Markdown selon les sections suivantes :\n\n"
                f"{schema_description}\n\n"
                "**IMPORTANT** :\n"
                "- Réponds UNIQUEMENT en format Markdown, pas en JSON\n"
                "- Utilise des titres (##, ###), des listes, des tableaux Markdown pour présenter les informations\n"
                "- Inclus les URLs des sources comme liens Markdown [texte](url)\n"
                "- Structure clairement chaque section avec des titres appropriés\n"
                "- Respecte les champs requis mentionnés ci-dessus"
            )
        
        # Charger les outils Agno si configurés
        agno_tools = []
        if config.tools:
            # Normaliser les noms d'outils (supprimer les backticks et descriptions si présents)
            normalized_tools = []
            for tool in config.tools:
                # Extraire juste le nom si format `tool_name` ou `tool_name` - description
                import re
                match = re.match(r'^`?([a-zA-Z_][a-zA-Z0-9_]*)`?', tool)
                if match:
                    normalized_tools.append(match.group(1))
                else:
                    normalized_tools.append(tool)
            
            logger.info(f"[ConfigurableAgent] 🔧 Outils demandés (normalisés): {normalized_tools}")
            
            # Vérifier si des outils de recherche web sont demandés
            web_search_tools = ["web_search", "web_search_news", "search_news", "duckduckgo_search", "duckduckgo_news"]
            has_web_search = any(tool in web_search_tools for tool in normalized_tools)
            
            if has_web_search:
                try:
                    import json
                    from agno.tools.duckduckgo import DuckDuckGoTools
                    try:
                        from ddgs.exceptions import DDGSException
                    except ImportError:
                        DDGSException = Exception  # fallback si ddgs n'expose pas l'exception

                    class DuckDuckGoToolsResilient(DuckDuckGoTools):
                        """Sous-classe d'Agno DuckDuckGoTools qui intercepte DDGSException (No results found) pour ne pas faire échouer l'agent."""

                        def duckduckgo_search(self, query: str, max_results: int = 5) -> str:
                            try:
                                return super().duckduckgo_search(query=query, max_results=max_results)
                            except DDGSException as e:
                                logger.warning("[ConfigurableAgent] DuckDuckGo search: %s", e)
                                return json.dumps(
                                    [{"title": "Aucun résultat", "body": "DuckDuckGo n'a pas retourné de résultats pour cette requête. Reformule ou continue sans."}],
                                    indent=2,
                                    ensure_ascii=False,
                                )

                        def duckduckgo_news(self, query: str, max_results: int = 5) -> str:
                            try:
                                return super().duckduckgo_news(query=query, max_results=max_results)
                            except DDGSException as e:
                                logger.warning("[ConfigurableAgent] DuckDuckGo news: %s", e)
                                return json.dumps(
                                    [{"title": "Aucun résultat", "body": "DuckDuckGo n'a pas retourné d'actualités pour cette requête. Reformule ou continue sans."}],
                                    indent=2,
                                    ensure_ascii=False,
                                )

                    duckduckgo_toolkit = DuckDuckGoToolsResilient()
                    agno_tools.append(duckduckgo_toolkit)
                    logger.info(f"[ConfigurableAgent] ✅ Outil DuckDuckGoTools (Agno) configuré")
                    logger.info(f"[ConfigurableAgent]   - duckduckgo_search: activé")
                    logger.info(f"[ConfigurableAgent]   - duckduckgo_news: activé")
                except ImportError as e:
                    logger.error(f"[ConfigurableAgent] ❌ DuckDuckGoTools d'Agno non disponible: {e}")
                    logger.error(f"[ConfigurableAgent] Installation requise: pip install ddgs")
                except Exception as e:
                    logger.error(f"[ConfigurableAgent] ❌ Erreur lors de la configuration de DuckDuckGoTools: {e}", exc_info=True)

            # Vérifier si des outils météo sont demandés
            weather_tools = ["weather", "meteo", "get_weather_forecast"]
            has_weather = any(tool in weather_tools for tool in normalized_tools)
            if has_weather:
                try:
                    from app.tools.weather_tools import WeatherTools
                    weather_toolkit = WeatherTools()
                    agno_tools.append(weather_toolkit)
                    logger.info(f"[ConfigurableAgent] ✅ Outil WeatherTools configuré")
                    logger.info(f"[ConfigurableAgent]   - get_weather_forecast: activé")
                except ImportError as e:
                    logger.error(f"[ConfigurableAgent] ❌ WeatherTools non disponible: {e}")
                except Exception as e:
                    logger.error(f"[ConfigurableAgent] ❌ Erreur lors de la configuration de WeatherTools: {e}", exc_info=True)
            
            # Vérifier si des outils de scraping d'offres d'emploi sont demandés
            job_scraping_tools = ["scrape_job_offers", "job_scraping", "list_saved_offers", "send_job_matching_email"]
            has_job_scraping = any(tool in job_scraping_tools for tool in normalized_tools)
            
            if has_job_scraping:
                try:
                    from app.tools.job_scraping_tools import JobScrapingTools
                    paths = self._scraper_paths_from_markdown(config.markdown_config)
                    parsed = self.parser.parse_markdown(config.markdown_config) if config.markdown_config else {}
                    agent_config_dict = {
                        "scrapers": paths,
                        "storage": parsed.get("storage") or getattr(config, "storage", None),
                    }
                    job_scraping_toolkit = JobScrapingTools(agent_config=agent_config_dict)
                    agno_tools.append(job_scraping_toolkit)
                    logger.info(f"[ConfigurableAgent] ✅ Outils JobScrapingTools configurés")
                    logger.info(f"[ConfigurableAgent]   - scrape_job_offers: activé")
                    logger.info(f"[ConfigurableAgent]   - list_saved_offers: activé")
                    logger.info(f"[ConfigurableAgent]   - send_job_matching_email: activé")
                except ImportError as e:
                    logger.error(f"[ConfigurableAgent] ❌ JobScrapingTools non disponible: {e}")
                    logger.error(f"[ConfigurableAgent] Installation requise: pip install playwright")
                except Exception as e:
                    logger.error(f"[ConfigurableAgent] ❌ Erreur lors de la configuration de JobScrapingTools: {e}", exc_info=True)
            
            # Ajouter des informations sur les outils disponibles dans les instructions
            if agno_tools:
                tools_list = ", ".join(normalized_tools)
                
                # Instructions spécifiques pour les outils de scraping d'emploi
                if has_job_scraping:
                    instructions_parts.append(
                        f"\n🔧 Outils de scraping d'offres d'emploi disponibles et ACTIFS:\n"
                        "IMPORTANT: Tu DOIS utiliser l'outil scrape_job_offers pour obtenir des offres d'emploi réelles.\n"
                        "\nLes outils suivants sont disponibles et fonctionnels:\n"
                        "- scrape_job_offers: Scrape les offres depuis Cadre Emploi\n"
                        "  Paramètres: keywords (ex: 'RH', 'Ressources Humaines'), location (ex: 'Paris')\n"
                        "- list_saved_offers: Liste les offres déjà sauvegardées\n"
                        "- send_job_matching_email: Envoie un email avec les résultats du matching\n"
                        "\nINSTRUCTIONS D'UTILISATION OBLIGATOIRES:\n"
                        "1. COMMENCE TOUJOURS par appeler scrape_job_offers avec les keywords et location du candidat\n"
                        "2. Analyse les offres obtenues (utilise read_offer_content si nécessaire)\n"
                        "3. Calcule les scores de compatibilité pour chaque offre\n"
                        "4. Construis ta réponse avec les offres réelles scrapées\n"
                        "\n⚠️ NE PAS répondre sans avoir appelé scrape_job_offers d'abord !\n"
                        "Les outils sont automatiquement disponibles - appelle-les AVANT de répondre."
                    )
                
                # Instructions pour les outils de recherche web
                if has_web_search:
                    instructions_parts.append(
                        f"\n🔧 Outils de recherche web disponibles et ACTIFS:\n"
                        "IMPORTANT: Tu DOIS utiliser les outils de recherche web pour obtenir des informations à jour.\n"
                        "Les outils suivants sont disponibles et fonctionnels:\n"
                        "- duckduckgo_search: Recherche web générale (utilise cet outil pour rechercher des informations)\n"
                        "- duckduckgo_news: Recherche d'actualités récentes (utilise cet outil pour les dernières nouvelles)\n"
                        "\nINSTRUCTIONS D'UTILISATION:\n"
                        "1. COMMENCE par utiliser duckduckgo_search ou duckduckgo_news avec une requête pertinente\n"
                        "2. Analyse les résultats obtenus\n"
                        "3. Utilise ces informations récentes pour construire ta réponse\n"
                        "4. Cite les URLs exactes des sources dans ta réponse JSON\n"
                        "\nLes outils sont automatiquement disponibles - appelle-les AVANT de répondre."
                    )

                # Instructions pour les outils météo
                if has_weather:
                    instructions_parts.append(
                        "\n🔧 Outil météo disponible et ACTIF:\n"
                        "IMPORTANT: Tu DOIS utiliser l'outil get_weather_forecast pour obtenir la météo réelle.\n"
                        "- get_weather_forecast: Donne la météo du jour et de la semaine à venir pour une ville.\n"
                        "  Paramètre: location (ex: Paris, Lyon, Bordeaux, Londres).\n"
                        "\nINSTRUCTIONS:\n"
                        "1. Appelle get_weather_forecast avec la localisation fournie par l'utilisateur (ville ou lieu)\n"
                        "2. Résume la météo du jour puis les prochains jours de façon claire\n"
                        "3. Réponds en français, de façon structurée\n"
                        "\nLes données proviennent d'Open-Meteo (gratuit, sans clé API)."
                    )
            else:
                # Si aucun outil n'a pu être chargé, mentionner dans les instructions
                tools_list = ", ".join(normalized_tools)
                instructions_parts.append(
                    f"\n⚠️  Outils demandés: {tools_list}\n"
                    "Note: Ces outils nécessitent une configuration supplémentaire pour fonctionner.\n"
                    "Pour activer les outils de recherche, installez: pip install ddgs"
                )
        
        # Ajouter des informations sur les serveurs MCP
        if config.mcp_servers:
            mcp_list = ", ".join(config.mcp_servers)
            instructions_parts.append(
                f"\nServeurs MCP disponibles: {mcp_list}\n"
                "Ces serveurs MCP fournissent des ressources et des outils supplémentaires."
            )
        
        instructions = "\n\n".join(instructions_parts) if instructions_parts else None
        
        # Créer l'agent avec les outils Agno
        agent_kwargs = {
            "name": config.name,
            "model": model,
            "instructions": instructions,
        }
        
        # Ajouter les outils Agno si disponibles
        if agno_tools:
            agent_kwargs["tools"] = agno_tools
            logger.info(f"[ConfigurableAgent] Outils Agno ajoutés à l'agent {config.name}: {[type(t).__name__ for t in agno_tools]}")
        
        return Agent(**agent_kwargs)
    
    def _parse_output(self, output_raw: str, output_schema: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Parse la sortie de l'agent selon le schéma défini"""
        # Si pas de schéma, retourner le Markdown brut
        if not output_schema:
            return {"markdown": output_raw, "format": "markdown"}
        
        # Détecter si la sortie est en Markdown (pas de JSON)
        import re
        # Si la sortie commence par un titre Markdown (#) ou contient des liens Markdown [](), c'est du Markdown
        # Ou si elle ne commence pas par { (JSON)
        output_stripped = output_raw.strip()
        is_markdown = (
            output_stripped.startswith('#') or 
            re.search(r'\[.*?\]\(https?://', output_raw) or
            re.search(r'^##', output_raw, re.MULTILINE) or
            (not output_stripped.startswith('{') and not output_stripped.startswith('['))
        )
        
        if is_markdown:
            logger.info(f"[ConfigurableAgent] ✅ Sortie détectée comme Markdown ({len(output_raw)} caractères)")
            logger.debug(f"[ConfigurableAgent] Premiers 200 caractères: {output_raw[:200]}")
            return {"markdown": output_raw, "format": "markdown"}
        
        # Sinon, essayer de parser comme JSON
        try:
            # Nettoyer le JSON en supprimant les commentaires et code blocks
            cleaned_output = output_raw
            
            # Supprimer les code blocks markdown
            import re
            json_match = re.search(r'```(?:json)?\n(.*?)\n```', cleaned_output, re.DOTALL)
            if json_match:
                cleaned_output = json_match.group(1)
            
            # Supprimer les commentaires JavaScript
            cleaned_output = re.sub(r'//.*?$', '', cleaned_output, flags=re.MULTILINE)
            cleaned_output = re.sub(r'/\*.*?\*/', '', cleaned_output, flags=re.DOTALL)
            
            # Nettoyer les virgules en fin de ligne
            cleaned_output = re.sub(r',\s*([}\]])', r'\1', cleaned_output)
            
            # Supprimer les caractères de contrôle invalides
            # JSON n'autorise que certains caractères de contrôle dans les chaînes (échappés: \n, \r, \t, etc.)
            # On va supprimer tous les caractères de contrôle non échappés
            cleaned_chars = []
            in_string = False
            escape_next = False
            
            for i, char in enumerate(cleaned_output):
                char_code = ord(char)
                
                # Gérer les guillemets pour savoir si on est dans une chaîne
                if char == '"' and not escape_next:
                    in_string = not in_string
                    cleaned_chars.append(char)
                    escape_next = False
                elif char == '\\' and in_string and not escape_next:
                    escape_next = True
                    cleaned_chars.append(char)
                elif escape_next:
                    # Caractère échappé - garder tel quel
                    cleaned_chars.append(char)
                    escape_next = False
                elif char_code >= 32 or char in '\n\r\t':
                    # Caractère valide
                    cleaned_chars.append(char)
                elif char_code < 32:
                    # Caractère de contrôle invalide
                    # JSON n'autorise pas les caractères de contrôle non échappés dans les chaînes
                    # On les remplace par un espace dans les chaînes, ou on les supprime ailleurs
                    if in_string:
                        # Dans une chaîne JSON, remplacer par un espace (mais éviter les espaces multiples)
                        # Sauf si c'est juste après un caractère qui ne devrait pas avoir d'espace après
                        if cleaned_chars and cleaned_chars[-1] not in [' ', ':', ',', '{', '[']:
                            cleaned_chars.append(' ')
                        logger.debug(f"[ConfigurableAgent] Caractère de contrôle remplacé à la position {i}: code {char_code} (dans chaîne)")
                    else:
                        # En dehors d'une chaîne, supprimer complètement
                        logger.debug(f"[ConfigurableAgent] Caractère de contrôle supprimé à la position {i}: code {char_code} (hors chaîne)")
                else:
                    cleaned_chars.append(char)
            
            cleaned_output = ''.join(cleaned_chars)
            
            # Réparer les URLs cassées par des caractères de contrôle
            # Les URLs peuvent être cassées de plusieurs façons
            def repair_broken_urls(text):
                """Répare les URLs qui ont été cassées par des caractères de contrôle"""
                import re
                
                # Pattern 1: URL complètement vidée, guillemets vides suivis directement d'une clé JSON
                # Exemple: "url": ""reliability": "high" -> "url": "", "reliability": "high"
                # Ce pattern doit être le premier car il est le plus spécifique
                text = re.sub(r'"url":\s*""([a-z_]+)":', r'"url": "", "\1":', text)
                
                # Pattern 1b: Même chose mais avec des espaces
                text = re.sub(r'"url":\s*""\s*([a-z_]+)":', r'"url": "", "\1":', text)
                
                # Pattern 2: URL tronquée où "https://" est immédiatement suivi d'une clé JSON
                # Exemple: "url": "https://"reliability": "high" -> "url": "","reliability": "high"
                text = re.sub(r'"url":\s*"https://""([a-z_]+)":', r'"url": "", "\1":', text)
                text = re.sub(r'"url":\s*"http://""([a-z_]+)":', r'"url": "", "\1":', text)
                
                # Pattern 3: "https:" suivi d'un saut de ligne et d'un guillemet fermant
                text = re.sub(r'"https:(\s*\n\s*)"', r'""', text)
                text = re.sub(r'"http:(\s*\n\s*)"', r'""', text)
                
                # Pattern 4: "https:" suivi d'un saut de ligne puis d'autres caractères
                text = re.sub(r'"https:(\s*\n\s*)([^"]+)"', r'"https://\2"', text)
                text = re.sub(r'"http:(\s*\n\s*)([^"]+)"', r'"http://\2"', text)
                
                # Pattern 5: URLs incomplètes avec guillemets consécutifs
                text = re.sub(r'"https:"\s*"', r'"",', text)
                text = re.sub(r'"http:"\s*"', r'"",', text)
                
                # Pattern 6: URLs cassées où le domaine est absent
                # Exemple: "https://"reliability" -> on vide l'URL
                text = re.sub(r'"(https?://)"([a-z])', r'"", "\2', text)
                
                return text
            
            cleaned_output = repair_broken_urls(cleaned_output)
            
            # Nettoyer les espaces multiples, mais préserver les URLs complètes
            def clean_spaces_preserve_urls(text):
                """Nettoie les espaces multiples tout en préservant les URLs"""
                import re
                # Protéger les URLs complètes
                url_pattern = r'"https?://[^"]*"'
                urls = re.findall(url_pattern, text)
                placeholders = {}
                for idx, url in enumerate(urls):
                    placeholder = f"__URL_PLACEHOLDER_{idx}__"
                    placeholders[placeholder] = url
                    text = text.replace(url, placeholder, 1)
                
                # Nettoyer les espaces multiples (mais préserver les sauts de ligne)
                lines = text.split('\n')
                cleaned_lines = []
                for line in lines:
                    # Nettoyer les espaces multiples dans chaque ligne
                    cleaned_line = re.sub(r' {2,}', ' ', line)
                    cleaned_lines.append(cleaned_line)
                text = '\n'.join(cleaned_lines)
                
                # Restaurer les URLs
                for placeholder, url in placeholders.items():
                    text = text.replace(placeholder, url)
                
                return text
            
            cleaned_output = clean_spaces_preserve_urls(cleaned_output)
            
            # Essayer de parser directement
            try:
                parsed = json.loads(cleaned_output.strip())
                return parsed
            except json.JSONDecodeError as e:
                # Si ça échoue, essayer une approche plus agressive
                logger.debug(f"[ConfigurableAgent] Premier essai de parsing échoué: {e}")
                
                # Afficher le contexte autour de l'erreur pour debug
                error_pos = e.pos if hasattr(e, 'pos') else None
                if error_pos:
                    start = max(0, error_pos - 100)
                    end = min(len(cleaned_output), error_pos + 100)
                    context = cleaned_output[start:end]
                    logger.warning(f"[ConfigurableAgent] Contexte autour de l'erreur (pos {error_pos}, ligne {e.lineno}, colonne {e.colno}):")
                    logger.warning(f"[ConfigurableAgent] {repr(context)}")
                    # Afficher les codes des caractères problématiques
                    problematic_chars = [(i, char, ord(char)) for i, char in enumerate(context, start) if ord(char) < 32 and char not in '\n\r\t']
                    if problematic_chars:
                        logger.warning(f"[ConfigurableAgent] Caractères problématiques trouvés: {[(pos, code, repr(char)) for pos, char, code in problematic_chars]}")
                    # Afficher la ligne exacte de l'erreur
                    lines = cleaned_output.split('\n')
                    if e.lineno and e.lineno <= len(lines):
                        error_line = lines[e.lineno - 1]
                        logger.warning(f"[ConfigurableAgent] Ligne {e.lineno} (colonne {e.colno}): {repr(error_line)}")
                        if e.colno and e.colno <= len(error_line):
                            logger.warning(f"[ConfigurableAgent] Caractère problématique: {repr(error_line[e.colno-1])} (code {ord(error_line[e.colno-1])})")
                
                # Nettoyer tous les caractères de contrôle restants (sauf \n, \r, \t)
                cleaned_output = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', cleaned_output)
                
                # Essayer de parser à nouveau
                try:
                    parsed = json.loads(cleaned_output.strip())
                    logger.info(f"[ConfigurableAgent] ✅ Parsing réussi après nettoyage agressif")
                    return parsed
                except json.JSONDecodeError as e2:
                    logger.warning(f"[ConfigurableAgent] Parsing échoué même après nettoyage: {e2}")
                    # Dernière tentative : essayer d'extraire juste le JSON entre accolades
                    json_match = re.search(r'\{[\s\S]*\}', cleaned_output)
                    if json_match:
                        try:
                            parsed = json.loads(json_match.group(0))
                            logger.info(f"[ConfigurableAgent] ✅ Parsing réussi après extraction du JSON")
                            return parsed
                        except json.JSONDecodeError:
                            pass
            
            # Parser le JSON
            parsed = json.loads(cleaned_output.strip())
            return parsed
            
        except json.JSONDecodeError as e:
            logger.warning(f"[ConfigurableAgent] ❌ Erreur lors du parsing de la sortie JSON: {e}")
            logger.warning(f"[ConfigurableAgent] Position de l'erreur: ligne {e.lineno}, colonne {e.colno}")
            logger.debug(f"[ConfigurableAgent] Sortie brute (premiers 500 caractères): {output_raw[:500]}")
            logger.debug(f"[ConfigurableAgent] Sortie brute (autour de l'erreur): {output_raw[max(0, e.pos-100):e.pos+100]}")
            return None
        except Exception as e:
            logger.error(f"Erreur lors du parsing de la sortie: {e}")
            return None
    
    async def execute_agent(
        self,
        db: Session,
        agent_id: int,
        user_id: int,
        input_text: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Exécute un agent configurable avec le texte fourni.
        
        Args:
            db: Session de base de données
            agent_id: ID de l'agent configurable
            user_id: ID de l'utilisateur qui exécute
            input_text: Texte qui complète le prompt et spécialise la demande
            options: Options additionnelles pour l'exécution
            
        Returns:
            Dictionnaire avec les résultats de l'exécution
        """
        start_time = time.time()
        
        # Charger l'agent
        agent_config = db.query(ConfigurableAgent).filter(
            ConfigurableAgent.id == agent_id,
            ConfigurableAgent.is_active == True,
        ).first()
        
        if not agent_config:
            raise ValueError(f"Agent configurable avec ID {agent_id} non trouvé ou inactif")
        
        # Vérifier les permissions (si l'agent n'est pas public, seul le propriétaire peut l'utiliser)
        if not agent_config.is_public and agent_config.user_id != user_id:
            raise PermissionError(f"Vous n'êtes pas autorisé à exécuter cet agent")
        
        try:
            # Vérifier que le prompt_template existe et n'est pas vide
            prompt_template_len = len(agent_config.prompt_template) if agent_config.prompt_template else 0
            logger.info(f"[ConfigurableAgent] 📋 Prompt template dans la DB: {prompt_template_len} caractères")
            if not agent_config.prompt_template or prompt_template_len < 50:
                logger.warning(f"[ConfigurableAgent] ⚠️  Prompt template semble incomplet ({prompt_template_len} caractères)")
                logger.warning(f"[ConfigurableAgent] Contenu actuel: {agent_config.prompt_template[:500] if agent_config.prompt_template else 'VIDE'}")
                logger.warning(f"[ConfigurableAgent] 💡 Conseil: Rechargez les agents depuis les fichiers pour mettre à jour le prompt_template")
            else:
                logger.debug(f"[ConfigurableAgent] Prompt template (premiers 500 chars): {agent_config.prompt_template[:500]}")
            
            # Rendre le prompt avec le texte d'entrée et les options (exclure input_text des kwargs, déjà passé)
            logger.info(f"[ConfigurableAgent] 📥 Options reçues (agent_options): keys={list((options or {}).keys())}, raw={options}")
            opts = {k: v for k, v in (options or {}).items() if k != "input_text"}
            logger.info(f"[ConfigurableAgent] 📥 Opts pour template (sans input_text): keys={list(opts.keys())}, values={opts}")
            prompt = self.parser.render_prompt(
                agent_config.prompt_template,
                input_text,
                **opts,
            )
            
            logger.info(f"[ConfigurableAgent] 📝 Prompt rendu: {len(prompt)} caractères")
            # Extraire et logger la section "Contexte du candidat" pour vérifier les champs dynamiques
            if "Contexte du candidat" in prompt or "## Contexte" in prompt:
                ctx_start = prompt.find("Contexte du candidat") if "Contexte du candidat" in prompt else prompt.find("## Contexte")
                ctx_snippet = prompt[ctx_start:ctx_start + 800] if ctx_start >= 0 else prompt[:800]
                logger.info(f"[ConfigurableAgent] 📋 Snippet prompt (Contexte / champs dynamiques):\n{ctx_snippet}")
            else:
                logger.info(f"[ConfigurableAgent] 📋 Snippet prompt (800 premiers car.):\n{prompt[:800]}")
            
            # Pré-scraping des offres pour les agents Job Matcher (le LLM n'appelle pas les tools)
            norm_tools = []
            for t in (agent_config.tools or []):
                m = re.match(r'^`?([a-zA-Z_][a-zA-Z0-9_]*)`?', str(t))
                norm_tools.append(m.group(1) if m else t)
            job_scraping_names = ["scrape_job_offers", "job_scraping", "list_saved_offers", "send_job_matching_email"]
            has_job_scraping = any(x in job_scraping_names for x in norm_tools)
            if has_job_scraping and opts.get("keywords") and opts.get("location"):
                try:
                    from app.services.job_scraping.job_scraping_service import get_job_scraping_service
                    paths = self._scraper_paths_from_markdown(agent_config.markdown_config)
                    search_params = {
                        "keywords": str(opts["keywords"]).strip(),
                        "location": str(opts["location"]).strip(),
                    }
                    if opts.get("job_type"):
                        # Accept single value or list / comma-separated (ex. "CDI, CDD" ou ["CDI", "Freelance"])
                        raw = opts["job_type"]
                        if isinstance(raw, list):
                            jt_list = [str(x).strip() for x in raw if x]
                        else:
                            jt_list = [x.strip() for x in str(raw).split(",") if x.strip()]
                        if jt_list:
                            search_params["job_type"] = jt_list[0] if len(jt_list) == 1 else jt_list
                            # Cadre Emploi : tyc=1 CDI, 2 CDD, 7 Freelance, 8 Stage (cumulables : tyc=7,2,1)
                            tyc_map = {"cdi": 1, "cdd": 2, "freelance": 7, "stage": 8}
                            tyc_values = []
                            for jt in jt_list:
                                if jt.lower() in tyc_map and tyc_map[jt.lower()] not in tyc_values:
                                    tyc_values.append(tyc_map[jt.lower()])
                            if tyc_values:
                                search_params["tyc"] = ",".join(str(t) for t in tyc_values)
                    salary_raw = opts.get("salary") or ""
                    if isinstance(salary_raw, str) and salary_raw.strip():
                        match = re.search(r"\d+", salary_raw.strip())
                        if match:
                            search_params["salary_min"] = int(match.group(), 10)
                    # Construire les paramètres d'URL Cadre Emploi
                    # motscles : version URL-encoded des keywords
                    search_params["motscles"] = quote_plus(search_params["keywords"])
                    # reg : code région (ex. FR-J pour Île-de-France)
                    reg = ""
                    loc = search_params["location"].strip()
                    if re.match(r"^FR-[A-Z]$", loc, flags=re.IGNORECASE):
                        reg = loc.upper()
                    elif "ile de france" in loc.lower() or "île-de-france" in loc.lower() or "ile-de-france" in loc.lower():
                        reg = "FR-J"
                    search_params["reg"] = reg
                    # Garantir la présence des clés utilisées dans le template URL
                    search_params.setdefault("tyc", "")
                    if "salary_min" not in search_params:
                        search_params["salary_min"] = ""
                    logger.info(
                        "[ConfigurableAgent] 🚀 Pré-scraping des offres (keywords=%r, location=%r, job_type=%r, salary_min=%s, paths=%s)...",
                        search_params["keywords"], search_params["location"],
                        search_params.get("job_type"), search_params.get("salary_min"), paths,
                    )
                    svc = get_job_scraping_service()
                    scrape_results = await svc.scrape_multiple(
                        config_paths=paths,
                        search_params=search_params,
                        save_to_files=True,
                    )
                    total_offers = sum(r.offers_count for r in scrape_results.values())
                    logger.info("[ConfigurableAgent] ✅ Pré-scraping terminé: %d offres", total_offers)
                    parts = ["\n## Offres scrapées\n"]
                    for src, r in scrape_results.items():
                        parts.append(f"- **{src}**: {r.offers_count} offres")
                    parts.append(f"\n**Total**: {total_offers} offres.\n")
                    if total_offers == 0:
                        parts.append("Aucune offre trouvée pour ces critères. Recommande d'élargir keywords ou localisation.\n")
                    n = 0
                    max_offers = 30
                    max_desc = 400
                    for src, r in scrape_results.items():
                        for o in r.offers:
                            if n >= max_offers:
                                break
                            raw = (o.description or "").replace("\n", " ").strip()
                            desc = raw[:max_desc] + ("..." if len(raw) > max_desc else "")
                            parts.append(f"### {o.title} @ {o.company}")
                            parts.append(f"- Lieu: {o.location} | [Lien]({o.url})")
                            if o.salary:
                                parts.append(f"- Salaire: {o.salary}")
                            parts.append(f"- {desc}\n")
                            n += 1
                        if n >= max_offers:
                            break
                    if total_offers > 0 and n < total_offers:
                        parts.append(f"*… et {total_offers - n} autres offres.*\n")
                    inject = "\n".join(parts)
                    prompt = prompt + inject
                    logger.info("[ConfigurableAgent] 📋 %d offres injectées dans le prompt", n)
                except Exception as e:
                    logger.exception("[ConfigurableAgent] ❌ Pré-scraping échoué: %s", e)
                    prompt = prompt + "\n\n**Note**: Le scraping des offres a échoué (" + str(e) + "). Analyse le profil sans offres réelles.\n"
            
            # Note: Les outils WebSearchTools d'Agno sont maintenant intégrés directement dans l'agent
            tool_results = {}
            
            logger.info(f"[ConfigurableAgent] Exécution de l'agent '{agent_config.name}' (ID: {agent_id})")
            logger.info(f"[ConfigurableAgent] 📥 Input text: {input_text[:200]}{'...' if len(input_text) > 200 else ''}")
            
            # Afficher les outils disponibles pour l'agent AVANT le prompt
            if agent_config.tools:
                logger.info(f"[ConfigurableAgent] 🔧 Outils disponibles pour l'agent: {agent_config.tools}")
            else:
                logger.info(f"[ConfigurableAgent] 🔧 Aucun outil configuré pour cet agent")
            
            # Afficher le prompt_template AVANT le rendu pour debug
            if agent_config.prompt_template:
                logger.debug(f"[ConfigurableAgent] 📋 Prompt template (avant rendu, {len(agent_config.prompt_template)} caractères):\n{agent_config.prompt_template[:500]}{'...' if len(agent_config.prompt_template) > 500 else ''}")
            
            # Log des outils utilisés
            if tool_results:
                logger.info(f"[ConfigurableAgent] 🔧 Outils exécutés: {list(tool_results.keys())}")
                for tool_name, tool_result in tool_results.items():
                    if tool_result.get("success"):
                        logger.info(f"[ConfigurableAgent]   ✅ {tool_name}: {len(tool_result.get('results', []))} résultat(s)")
                    else:
                        logger.warning(f"[ConfigurableAgent]   ❌ {tool_name}: {tool_result.get('error', 'Erreur inconnue')}")
            
            logger.info(f"[ConfigurableAgent] 📝 Prompt complet ({len(prompt)} caractères):\n{'='*80}\n{prompt}\n{'='*80}")
            
            # Créer et exécuter l'agent Agno
            logger.info(f"[ConfigurableAgent] 🚀 Création de l'agent Agno...")
            agno_agent = self._create_agent(agent_config)
            
            # Construire le prompt complet qui sera réellement envoyé
            # Les instructions de l'agent sont dans agno_agent.instructions
            # Le prompt rendu est ce qui sera passé à run()
            full_prompt_parts = []
            if hasattr(agno_agent, 'instructions') and agno_agent.instructions:
                if isinstance(agno_agent.instructions, list):
                    full_prompt_parts.extend(agno_agent.instructions)
                else:
                    full_prompt_parts.append(str(agno_agent.instructions))
            full_prompt_parts.append(prompt)
            full_prompt = "\n\n".join(full_prompt_parts)
            
            logger.info(f"[ConfigurableAgent] 📝 Prompt complet qui sera envoyé ({len(full_prompt)} caractères):\n{'='*80}\n{full_prompt}\n{'='*80}")
            
            tools_attached = getattr(agno_agent, "tools", None) or []
            tool_names = []
            for t in tools_attached:
                name = getattr(t, "name", None) or getattr(t, "__name__", None) or type(t).__name__
                if hasattr(t, "tools") and t.tools:
                    tool_names.extend([getattr(s, "name", str(s)) for s in t.tools])
                else:
                    tool_names.append(str(name))
            logger.info(f"[ConfigurableAgent] 🔧 Outils Agno attachés à l'agent: {tool_names}")

            if self.settings.skip_agent_llm:
                logger.info("[ConfigurableAgent] ⏭️ SKIP_AGENT_LLM activé : appel LLM désactivé (économie de coûts)")
                output_raw = "[Appel LLM désactivé - SKIP_AGENT_LLM=true. Pré-scraping exécuté si configuré.]"
                response = type("MockResponse", (), {"content": output_raw, "run_id": None, "messages": [], "tool_calls": []})()
            else:
                logger.info(f"[ConfigurableAgent] ⏳ Exécution de l'agent (peut prendre plusieurs secondes)...")
                response = agno_agent.run(prompt)
            
            output_raw = response.content if hasattr(response, "content") else str(response)
            resp_attrs = {}
            for k in ("run_id", "messages", "tool_calls"):
                if hasattr(response, k):
                    v = getattr(response, k)
                    resp_attrs[k] = f"list(len={len(v)})" if isinstance(v, list) else v
            logger.info(f"[ConfigurableAgent] 📤 Réponse Agno: type={type(response).__name__}, content len={len(output_raw)}, attrs={resp_attrs}")
            logger.info(f"[ConfigurableAgent] 📤 Réponse reçue (longueur: {len(output_raw)} caractères)")
            logger.info(f"[ConfigurableAgent] 📄 Sortie brute:\n{'='*80}\n{output_raw}\n{'='*80}")
            
            # Parser la sortie selon le schéma
            output_parsed = None
            if agent_config.output_schema:
                logger.info(f"[ConfigurableAgent] 🔍 Tentative de parsing selon le schéma défini...")
                logger.debug(f"[ConfigurableAgent] Schéma attendu: {json.dumps(agent_config.output_schema, indent=2, ensure_ascii=False)}")
                output_parsed = self._parse_output(output_raw, agent_config.output_schema)
                if output_parsed:
                    logger.info(f"[ConfigurableAgent] ✅ Sortie parsée avec succès")
                    logger.info(f"[ConfigurableAgent] 📊 Données parsées:\n{json.dumps(output_parsed, indent=2, ensure_ascii=False)}")
                else:
                    logger.warning(f"[ConfigurableAgent] ⚠️  Échec du parsing de la sortie selon le schéma")
                    logger.debug(f"[ConfigurableAgent] Sortie brute complète (pour debug):\n{output_raw}")
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Logger l'exécution
            execution_log = AgentExecutionLog(
                agent_id=agent_id,
                user_id=user_id,
                input_text=input_text,
                prompt_used=prompt,
                output_raw=output_raw,
                output_parsed=output_parsed,
                success=True,
                execution_time_ms=execution_time_ms,
            )
            db.add(execution_log)
            db.commit()
            
            logger.info(f"[ConfigurableAgent] ✅ Exécution terminée en {execution_time_ms}ms")
            logger.info(f"[ConfigurableAgent] 📋 Résumé:")
            logger.info(f"   - Agent: {agent_config.name} (ID: {agent_id})")
            logger.info(f"   - Input: {input_text[:100]}{'...' if len(input_text) > 100 else ''}")
            logger.info(f"   - Sortie brute: {len(output_raw)} caractères")
            logger.info(f"   - Sortie parsée: {'✅ Oui' if output_parsed else '❌ Non'}")
            logger.info(f"   - Temps d'exécution: {execution_time_ms}ms")
            
            return {
                "success": True,
                "agent_id": agent_id,
                "agent_name": agent_config.name,
                "input_text": input_text,
                "prompt_used": prompt,
                "output_raw": output_raw,
                "output_parsed": output_parsed,
                "tool_results": tool_results if tool_results else None,
                "execution_time_ms": execution_time_ms,
            }
            
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            error_message = str(e)
            
            logger.error(f"[ConfigurableAgent] ❌ Erreur lors de l'exécution: {error_message}", exc_info=True)
            logger.error(f"[ConfigurableAgent] 📋 Détails de l'erreur:")
            logger.error(f"   - Agent: {agent_config.name} (ID: {agent_id})")
            logger.error(f"   - Input: {input_text[:100]}{'...' if len(input_text) > 100 else ''}")
            logger.error(f"   - Prompt utilisé: {'Oui' if 'prompt' in locals() else 'Non'}")
            if 'prompt' in locals():
                logger.error(f"   - Longueur du prompt: {len(prompt)} caractères")
            logger.error(f"   - Temps écoulé avant l'erreur: {execution_time_ms}ms")
            logger.error(f"   - Type d'erreur: {type(e).__name__}")
            
            # Logger l'erreur
            execution_log = AgentExecutionLog(
                agent_id=agent_id,
                user_id=user_id,
                input_text=input_text,
                prompt_used=prompt if 'prompt' in locals() else "",
                output_raw=None,
                output_parsed=None,
                success=False,
                error_message=error_message,
                execution_time_ms=execution_time_ms,
            )
            db.add(execution_log)
            db.commit()
            
            raise


# Instance singleton
configurable_agent_service = ConfigurableAgentService()
