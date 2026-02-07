from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
from pathlib import Path

from app.api.deps import get_current_user
from app.models.user import User
from app.core.config import get_settings as get_settings_config

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    # Email
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    imap_user: Optional[str] = None
    imap_password: Optional[str] = None
    imap_folder: Optional[str] = None
    imap_ssl: Optional[bool] = None
    imap_poll_minutes: Optional[int] = None
    
    # AI
    agno_model: Optional[str] = None
    agno_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None
    ollama_base_url: Optional[str] = None
    
    # Web Search
    google_search_api_key: Optional[str] = None
    google_search_engine_id: Optional[str] = None
    bing_search_api_key: Optional[str] = None
    search_provider: Optional[str] = None


class SettingsResponse(BaseModel):
    # Email
    imap_host: str
    imap_port: int
    imap_user: str
    imap_password: str  # Masqué
    imap_folder: str
    imap_ssl: bool
    imap_poll_minutes: int
    
    # AI
    agno_model: str
    agno_api_key: str  # Masqué
    openai_api_key: str  # Masqué
    mistral_api_key: str  # Masqué
    ollama_base_url: str
    
    # Web Search
    google_search_api_key: str  # Masqué
    google_search_engine_id: str
    bing_search_api_key: str  # Masqué
    search_provider: str


@router.get("", response_model=SettingsResponse)
async def get_settings(current_user: User = Depends(get_current_user)):
    """Récupère les paramètres (masque les mots de passe)"""
    settings = get_settings_config()
    return SettingsResponse(
        imap_host=settings.imap_host,
        imap_port=settings.imap_port,
        imap_user=settings.imap_user,
        imap_password="***" if settings.imap_password else "",
        imap_folder=settings.imap_folder,
        imap_ssl=settings.imap_ssl,
        imap_poll_minutes=settings.imap_poll_minutes,
        agno_model=settings.agno_model,
        agno_api_key="***" if settings.agno_api_key else "",
        openai_api_key="***" if settings.openai_api_key else "",
        mistral_api_key="***" if settings.mistral_api_key else "",
        ollama_base_url=settings.ollama_base_url or "",
        google_search_api_key="***" if settings.google_search_api_key else "",
        google_search_engine_id=settings.google_search_engine_id,
        bing_search_api_key="***" if settings.bing_search_api_key else "",
        search_provider=settings.search_provider,
    )


@router.post("")
async def update_settings(
    settings_update: SettingsUpdate,
    current_user: User = Depends(get_current_user)
):
    """Met à jour les paramètres dans le fichier .env"""
    # Vérifier que l'utilisateur est admin (optionnel)
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="Accès refusé")
    
    env_file = Path(__file__).parent.parent.parent / ".env"
    
    # Lire le fichier .env existant
    env_vars = {}
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    
    # Mettre à jour les valeurs
    update_dict = settings_update.model_dump(exclude_none=True)
    
    # Mapper les noms de champs vers les noms de variables d'environnement
    field_mapping = {
        'imap_host': 'IMAP_HOST',
        'imap_port': 'IMAP_PORT',
        'imap_user': 'IMAP_USER',
        'imap_password': 'IMAP_PASSWORD',
        'imap_folder': 'IMAP_FOLDER',
        'imap_ssl': 'IMAP_SSL',
        'imap_poll_minutes': 'IMAP_POLL_MINUTES',
        'agno_model': 'AGNO_MODEL',
        'agno_api_key': 'AGNO_API_KEY',
        'openai_api_key': 'OPENAI_API_KEY',
        'mistral_api_key': 'MISTRAL_API_KEY',
        'ollama_base_url': 'OLLAMA_BASE_URL',
        'google_search_api_key': 'GOOGLE_SEARCH_API_KEY',
        'google_search_engine_id': 'GOOGLE_SEARCH_ENGINE_ID',
        'bing_search_api_key': 'BING_SEARCH_API_KEY',
        'search_provider': 'SEARCH_PROVIDER',
    }
    
    for field, value in update_dict.items():
        env_key = field_mapping.get(field)
        if env_key:
            if isinstance(value, bool):
                env_vars[env_key] = str(value).lower()
            else:
                env_vars[env_key] = str(value)
    
    # Écrire le fichier .env
    with open(env_file, 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    return {"message": "Paramètres mis à jour avec succès", "note": "Redémarrez le serveur pour appliquer les changements"}


@router.post("/test/{service}")
async def test_connection(
    service: str,
    current_user: User = Depends(get_current_user)
):
    """Teste la connexion d'un service"""
    settings = get_settings_config()
    
    if service == "email":
        try:
            import imaplib
            if settings.imap_ssl:
                mail = imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port)
            else:
                mail = imaplib.IMAP4(settings.imap_host, settings.imap_port)
            mail.login(settings.imap_user, settings.imap_password)
            mail.logout()
            return {"status": "success", "message": "Connexion IMAP réussie"}
        except Exception as e:
            return {"status": "error", "message": f"Erreur de connexion: {str(e)}"}
    
    elif service == "ai":
        from app.core.agno_model import is_ollama_configured
        if is_ollama_configured():
            return {"status": "success", "message": "Ollama configuré (OLLAMA_BASE_URL)"}
        if not settings.agno_api_key and not settings.openai_api_key:
            return {"status": "error", "message": "Aucune clé API configurée (ou définir OLLAMA_BASE_URL pour Ollama)"}
        return {"status": "success", "message": "Clés API configurées"}
    
    elif service == "web_search":
        if settings.search_provider == "google":
            if not settings.google_search_api_key or not settings.google_search_engine_id:
                return {"status": "error", "message": "Configuration Google incomplète"}
        elif settings.search_provider == "bing":
            if not settings.bing_search_api_key:
                return {"status": "error", "message": "Clé API Bing manquante"}
        return {"status": "success", "message": f"Configuration {settings.search_provider} valide"}
    
    raise HTTPException(status_code=400, detail=f"Service inconnu: {service}")
