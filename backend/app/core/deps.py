import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    logger.info(f"🔐 [Auth] get_current_user appelé")
    logger.info(f"🔐 [Auth] Token reçu (premiers 20 chars): {token[:20] if token else 'None'}...")
    
    # Vérifier que la clé secrète JWT est configurée
    if not settings.jwt_secret_key or settings.jwt_secret_key == "":
        logger.error(f"🔐 [Auth] ❌ JWT_SECRET_KEY n'est pas configuré dans les variables d'environnement !")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configuration serveur invalide : JWT_SECRET_KEY manquant",
        )
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        logger.info(f"🔐 [Auth] Tentative de décodage du token avec secret_key: {settings.jwt_secret_key[:10] if len(settings.jwt_secret_key) > 10 else '***'}...")
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        logger.info(f"🔐 [Auth] Token décodé avec succès, payload: {payload}")
        username: str | None = payload.get("sub")
        if username is None:
            logger.error(f"🔐 [Auth] ❌ Username manquant dans le payload")
            raise credentials_exception
        logger.info(f"🔐 [Auth] ✅ Authentification réussie pour utilisateur: {username}")
        return username
    except JWTError as exc:
        logger.error(f"🔐 [Auth] ❌ Erreur JWT: {exc}")
        logger.error(f"🔐 [Auth] ❌ Détails: secret_key présent={bool(settings.jwt_secret_key)}, longueur={len(settings.jwt_secret_key) if settings.jwt_secret_key else 0}")
        raise credentials_exception from exc
