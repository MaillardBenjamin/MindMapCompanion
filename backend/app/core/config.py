import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).parent.parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        extra="ignore",
        populate_by_name=True  # Permet d'utiliser soit l'alias soit le nom du champ
    )

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/personal_assistant",
        alias="DATABASE_URL"
    )

    jwt_secret_key: str = Field(default="", alias="SECRET_KEY")  # Utilise SECRET_KEY du .env
    jwt_algorithm: str = Field(default="HS256", alias="ALGORITHM")
    jwt_exp_minutes: int = Field(default=60 * 24, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    auth_username: str = Field(default="", alias="AUTH_USERNAME")
    auth_password: str = Field(default="", alias="AUTH_PASSWORD")

    imap_host: str = Field(default="", alias="IMAP_HOST")
    imap_port: int = Field(default=993, alias="IMAP_PORT")
    imap_user: str = Field(default="", alias="IMAP_USER")
    imap_password: str = Field(default="", alias="IMAP_PASSWORD")
    imap_folder: str = Field(default="INBOX", alias="IMAP_FOLDER")
    imap_ssl: bool = Field(default=True, alias="IMAP_SSL")
    imap_poll_minutes: int = Field(default=2, alias="IMAP_POLL_MINUTES")

    # AI Agents configuration
    skip_agent_llm: bool = Field(default=False, alias="SKIP_AGENT_LLM")
    # Supervision site : régénérations LLM du plan après échec Playwright (0 = désactivé)
    site_health_max_repairs: int = Field(default=2, alias="SITE_HEALTH_MAX_REPAIRS")
    # Capture PNG à l’échec d’une étape (pour réparation vision / logs)
    site_health_failure_screenshot: bool = Field(default=True, alias="SITE_HEALTH_FAILURE_SCREENSHOT")
    # Joindre la capture au LLM de réparation (désactiver si modèle sans vision, ex. Ollama texte seul)
    site_health_repair_with_screenshot: bool = Field(default=True, alias="SITE_HEALTH_REPAIR_WITH_SCREENSHOT")
    agno_model: str = Field(default="gpt-5-mini", alias="AGNO_MODEL")
    agno_api_key: str = Field(default="", alias="AGNO_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    mistral_api_key: str = Field(default="", alias="MISTRAL_API_KEY")
    # Ollama (modèle local) : si défini, Agno utilise cette URL au lieu d'OpenAI (ex: http://localhost:11434/v1)
    ollama_base_url: str = Field(default="", alias="OLLAMA_BASE_URL")

    # Web Search APIs configuration
    google_search_api_key: str = Field(default="", alias="GOOGLE_SEARCH_API_KEY")
    google_search_engine_id: str = Field(default="", alias="GOOGLE_SEARCH_ENGINE_ID")
    bing_search_api_key: str = Field(default="", alias="BING_SEARCH_API_KEY")
    search_provider: str = Field(default="google", alias="SEARCH_PROVIDER")

    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")

    # GitHub (lecture API : audit commit, dépôts privés)
    github_token: str = Field(default="", alias="GITHUB_TOKEN")


@lru_cache
def get_settings() -> Settings:
    return Settings()
