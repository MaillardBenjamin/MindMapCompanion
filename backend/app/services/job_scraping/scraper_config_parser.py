"""
Parser de configuration pour les scrapers Playwright.

Parse les fichiers markdown de configuration des scrapers et les convertit
en objets exécutables par le PlaywrightExecutor.
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

import yaml

logger = logging.getLogger(__name__)


@dataclass
class BrowserConfig:
    """Configuration du navigateur Playwright"""
    headless: bool = False
    viewport: Dict[str, int] = field(default_factory=lambda: {"width": 1920, "height": 1080})
    user_agent: Optional[str] = None
    timeout: int = 30000
    navigation_timeout: int = 60000
    wait_until: str = "networkidle"  # load, domcontentloaded, networkidle, commit
    
    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "BrowserConfig":
        if not data:
            return cls()
        return cls(
            headless=data.get("headless", False),
            viewport=data.get("viewport", {"width": 1920, "height": 1080}),
            user_agent=data.get("user_agent"),
            timeout=data.get("timeout", 30000),
            navigation_timeout=data.get("navigation_timeout", 60000),
            wait_until=data.get("wait_until", "networkidle"),
        )


@dataclass
class CredentialsConfig:
    """Configuration des credentials (référence aux env vars)"""
    email_env: Optional[str] = None
    password_env: Optional[str] = None
    extra: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "CredentialsConfig":
        if not data:
            return cls()
        return cls(
            email_env=data.get("email_env"),
            password_env=data.get("password_env"),
            extra={k: v for k, v in data.items() if k not in ["email_env", "password_env"]},
        )


@dataclass
class StorageConfig:
    """Configuration du stockage des offres"""
    base_dir: str = "data/job_offers"
    subdir_pattern: str = "{date}"
    file_pattern: str = "{title_slug}-{id}.md"
    archive_dir: Optional[str] = None
    retention_days: int = 30
    cleanup_enabled: bool = True
    cleanup_schedule: str = "0 2 * * 0"
    
    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "StorageConfig":
        if not data:
            return cls()
        return cls(
            base_dir=data.get("base_dir", "data/job_offers"),
            subdir_pattern=data.get("subdir_pattern", "{date}"),
            file_pattern=data.get("file_pattern", "{title_slug}-{id}.md"),
            archive_dir=data.get("archive_dir"),
            retention_days=data.get("retention_days", 30),
            cleanup_enabled=data.get("cleanup_enabled", True),
            cleanup_schedule=data.get("cleanup_schedule", "0 2 * * 0"),
        )


@dataclass
class PlaywrightStep:
    """Une étape d'exécution Playwright"""
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    wait_for: Optional[Dict[str, Any]] = None
    on_error: Optional[List[Dict[str, Any]]] = None
    condition: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlaywrightStep":
        action = data.pop("action", "unknown")
        wait_for = data.pop("wait_for", None)
        on_error = data.pop("on_error", None)
        condition = data.pop("condition", None)
        
        return cls(
            action=action,
            params=data,
            wait_for=wait_for,
            on_error=on_error,
            condition=condition,
        )


@dataclass
class ScraperConfig:
    """Configuration complète d'un scraper"""
    name: str
    site_url: str
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    credentials: CredentialsConfig = field(default_factory=CredentialsConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    steps: List[PlaywrightStep] = field(default_factory=list)
    anti_bot: Dict[str, Any] = field(default_factory=dict)
    rate_limiting: Dict[str, Any] = field(default_factory=dict)
    error_handling: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ScraperConfigParser:
    """
    Parse les fichiers markdown de configuration des scrapers.
    
    Format attendu :
    ---
    name: Nom du scraper
    site_url: https://example.com
    browser:
      headless: false
      ...
    credentials:
      email_env: ENV_VAR_NAME
      ...
    storage:
      base_dir: data/job_offers
      ...
    ---
    
    # Instructions Playwright
    
    ## Section
    
    ### Étape N: Description
    ```yaml
    action: goto
    url: "{{site_url}}"
    ...
    ```
    """
    
    def __init__(self, examples_dir: Optional[Path] = None):
        """
        Initialise le parser.
        
        Args:
            examples_dir: Répertoire contenant les fichiers de config
        """
        if examples_dir is None:
            examples_dir = Path(__file__).parent.parent.parent / "agent_configs"
        self.examples_dir = examples_dir
    
    def load_config(self, config_path: str) -> ScraperConfig:
        """
        Charge une configuration depuis un fichier.
        
        Args:
            config_path: Chemin relatif depuis examples_dir ou chemin absolu
        
        Returns:
            Configuration parsée
        """
        # Résoudre le chemin
        path = Path(config_path)
        if not path.is_absolute():
            path = self.examples_dir / config_path
        
        if not path.exists():
            raise FileNotFoundError(f"Fichier de configuration non trouvé: {path}")
        
        content = path.read_text(encoding="utf-8")
        return self.parse_markdown(content)
    
    def parse_markdown(self, content: str) -> ScraperConfig:
        """
        Parse le contenu markdown d'une configuration.
        
        Args:
            content: Contenu markdown
        
        Returns:
            Configuration parsée
        """
        # Extraire le frontmatter
        frontmatter = {}
        body = content
        
        frontmatter_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
        if frontmatter_match:
            try:
                frontmatter = yaml.safe_load(frontmatter_match.group(1)) or {}
            except yaml.YAMLError as e:
                logger.warning(f"[ScraperConfigParser] Erreur parsing YAML frontmatter: {e}")
            body = content[frontmatter_match.end():]
        
        # Créer la configuration de base
        config = ScraperConfig(
            name=frontmatter.get("name", "Unknown Scraper"),
            site_url=frontmatter.get("site_url", ""),
            browser=BrowserConfig.from_dict(frontmatter.get("browser")),
            credentials=CredentialsConfig.from_dict(frontmatter.get("credentials")),
            storage=StorageConfig.from_dict(frontmatter.get("storage")),
            anti_bot=frontmatter.get("anti_bot", {}),
            rate_limiting=frontmatter.get("rate_limiting", {}),
            error_handling=frontmatter.get("error_handling", {}),
            metadata=frontmatter.get("metadata", {}),
        )
        
        # Parser les étapes depuis le corps du markdown
        config.steps = self._parse_steps(body)
        
        logger.info(f"[ScraperConfigParser] Configuration parsée: {config.name} avec {len(config.steps)} étapes")
        
        return config
    
    def _parse_steps(self, body: str) -> List[PlaywrightStep]:
        """
        Parse les étapes Playwright depuis le corps du markdown.
        
        Args:
            body: Corps du markdown (après le frontmatter)
        
        Returns:
            Liste des étapes
        """
        steps = []
        
        # Trouver tous les blocs de code YAML
        yaml_pattern = r'```yaml\n(.*?)\n```'
        matches = re.findall(yaml_pattern, body, re.DOTALL)
        
        for i, yaml_content in enumerate(matches):
            try:
                step_data = yaml.safe_load(yaml_content)
                if step_data and isinstance(step_data, dict):
                    # Vérifier si c'est une configuration globale ou une étape
                    if "action" in step_data:
                        step = PlaywrightStep.from_dict(step_data.copy())
                        steps.append(step)
                        logger.debug(f"[ScraperConfigParser] Étape {i+1} parsée: {step.action}")
                    else:
                        # C'est peut-être une config de section (anti_bot, rate_limiting, etc.)
                        logger.debug(f"[ScraperConfigParser] Bloc YAML sans action ignoré (config section)")
            except yaml.YAMLError as e:
                logger.warning(f"[ScraperConfigParser] Erreur parsing étape {i+1}: {e}")
            except Exception as e:
                logger.warning(f"[ScraperConfigParser] Erreur inattendue étape {i+1}: {e}")
        
        return steps
    
    def validate_config(self, config: ScraperConfig) -> tuple[bool, List[str]]:
        """
        Valide une configuration.
        
        Args:
            config: Configuration à valider
        
        Returns:
            (is_valid, list of errors)
        """
        errors = []
        
        if not config.name:
            errors.append("Le nom du scraper est requis")
        
        if not config.site_url:
            errors.append("L'URL du site est requise")
        
        if not config.steps:
            errors.append("Au moins une étape est requise")
        
        # Valider les étapes
        for i, step in enumerate(config.steps):
            if not step.action:
                errors.append(f"Étape {i+1}: action requise")
        
        return len(errors) == 0, errors
    
    def get_required_env_vars(self, config: ScraperConfig) -> List[str]:
        """
        Liste les variables d'environnement requises.
        
        Args:
            config: Configuration
        
        Returns:
            Liste des noms de variables d'environnement
        """
        env_vars = []
        
        if config.credentials.email_env:
            env_vars.append(config.credentials.email_env)
        if config.credentials.password_env:
            env_vars.append(config.credentials.password_env)
        
        for key, value in config.credentials.extra.items():
            if isinstance(value, str) and value.endswith("_env"):
                env_vars.append(value)
        
        return env_vars
    
    def list_available_configs(self, subdir: str = "scrapers") -> List[Path]:
        """
        Liste les fichiers de configuration disponibles.
        
        Args:
            subdir: Sous-répertoire à scanner
        
        Returns:
            Liste des chemins de fichiers
        """
        search_path = self.examples_dir / subdir
        if not search_path.exists():
            return []
        
        return list(search_path.glob("*.md"))


class TemplateResolver:
    """
    Résout les templates dans les valeurs de configuration.
    
    Supporte les patterns comme {{site_url}}, {{credentials.email}}, etc.
    """
    
    def __init__(self, context: Dict[str, Any]):
        """
        Initialise le resolver avec un contexte.
        
        Args:
            context: Dictionnaire de valeurs à utiliser pour la résolution
        """
        self.context = context
    
    def resolve(self, value: Any) -> Any:
        """
        Résout les templates dans une valeur.
        
        Args:
            value: Valeur avec potentiels templates
        
        Returns:
            Valeur avec templates résolus
        """
        if isinstance(value, str):
            return self._resolve_string(value)
        elif isinstance(value, dict):
            return {k: self.resolve(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.resolve(v) for v in value]
        else:
            return value
    
    def _resolve_string(self, text: str) -> str:
        """Résout les templates dans une chaîne"""
        pattern = r'\{\{([^}]+)\}\}'
        
        def replace_match(match):
            key = match.group(1).strip()
            value = self._get_nested_value(key)
            if value is not None:
                return str(value)
            else:
                logger.warning(f"[TemplateResolver] Variable non trouvée: {key}")
                return match.group(0)  # Garder le template original
        
        return re.sub(pattern, replace_match, text)
    
    def _get_nested_value(self, key: str) -> Any:
        """
        Récupère une valeur imbriquée depuis le contexte.
        
        Supporte les clés comme "credentials.email", "search.keywords", etc.
        """
        keys = key.split(".")
        value = self.context
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        
        return value

    def get(self, key: str) -> Any:
        """Récupère une valeur du contexte (clé imbriquée supportée)."""
        return self._get_nested_value(key)
    
    def add_to_context(self, key: str, value: Any):
        """Ajoute une valeur au contexte"""
        self.context[key] = value
    
    def update_context(self, updates: Dict[str, Any]):
        """Met à jour le contexte avec plusieurs valeurs"""
        self.context.update(updates)
