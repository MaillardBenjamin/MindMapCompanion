import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).parent.parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ENV_FILE) if ENV_FILE.exists() else None, extra="ignore")

    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/personal_assistant"
    )

    jwt_secret_key: str = ""  # Doit être défini dans .env
    jwt_algorithm: str = "HS256"
    jwt_exp_minutes: int = 60 * 24
    auth_username: str = ""  # Doit être défini dans .env
    auth_password: str = ""  # Doit être défini dans .env

    imap_host: str = ""  # Doit être défini dans .env
    imap_port: int = 993  # Port 993 pour IMAP SSL
    imap_user: str = ""  # Doit être défini dans .env
    imap_password: str = ""  # Doit être défini dans .env
    imap_folder: str = "INBOX"
    imap_ssl: bool = True
    imap_poll_minutes: int = 2

    # AI Agents configuration
    agno_model: str = "gpt-5-mini"
    agno_api_key: str = ""
    openai_api_key: str = ""
    mistral_api_key: str = ""

    # Web Search APIs configuration
    google_search_api_key: str = ""
    google_search_engine_id: str = ""
    bing_search_api_key: str = ""
    search_provider: str = "google"  # "google" or "bing"

    cors_origins: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()
