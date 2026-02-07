import logging
from datetime import datetime, timedelta

from jose import jwt

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def create_access_token(subject: str) -> str:
    if not settings.jwt_secret_key or settings.jwt_secret_key == "":
        logger.error("❌ [Security] JWT_SECRET_KEY n'est pas configuré ! Impossible de créer un token.")
        raise ValueError("JWT_SECRET_KEY n'est pas configuré dans les variables d'environnement")
    
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_exp_minutes)
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
