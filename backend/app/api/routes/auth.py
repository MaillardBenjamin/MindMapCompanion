import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, ProgrammingError
from app.database import get_db
from app.schemas.user import UserCreate, UserLogin
from app.schemas.token import Token, RefreshTokenRequest
from app.crud.user import (
    get_user_by_email,
    get_user_by_id,
    create_user,
    save_refresh_token,
    get_refresh_token,
    delete_refresh_token
)
from app.auth.password import verify_password
from app.auth.jwt_handler import create_access_token, create_refresh_token, verify_token
from datetime import timedelta
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """Création d'un nouveau compte utilisateur"""
    # Vérifier si l'utilisateur existe déjà
    db_user = get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un utilisateur avec cet email existe déjà"
        )
    
    # Créer l'utilisateur
    new_user = create_user(db, user)
    
    # Générer les tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.email, "user_id": new_user.id},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": new_user.email, "user_id": new_user.id}
    )
    
    # Sauvegarder le refresh token
    save_refresh_token(db, new_user.id, refresh_token)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/login", response_model=Token)
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Connexion d'un utilisateur"""
    logger.info("[Auth] login: entrée (email=%s)", user_credentials.email)
    try:
        logger.info("[Auth] login: appel get_user_by_email...")
        user = get_user_by_email(db, email=user_credentials.email)
        logger.info("[Auth] login: get_user_by_email ok, user=%s", user.id if user else None)
    except (OperationalError, ProgrammingError) as e:
        logger.exception("[Auth] login: erreur SQL (migration manquante ?): %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de données indisponible ou schéma obsolète. Exécutez: alembic upgrade head",
        ) from e
    except Exception as e:
        logger.exception("[Auth] login: erreur inattendue lors de get_user_by_email: %s", e)
        raise

    if not user:
        logger.warning("[Auth] login: utilisateur non trouvé (email=%s)", user_credentials.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect"
        )

    try:
        logger.info("[Auth] login: vérification mot de passe (user_id=%s)...", user.id)
        if not verify_password(user_credentials.password, user.hashed_password):
            logger.warning("[Auth] login: mot de passe incorrect (user_id=%s)", user.id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe incorrect"
            )
        logger.info("[Auth] login: mot de passe ok")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[Auth] login: erreur lors de verify_password: %s", e)
        raise

    if not user.is_active:
        logger.warning("[Auth] login: compte inactif (user_id=%s)", user.id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Compte utilisateur inactif"
        )

    try:
        logger.info("[Auth] login: génération des tokens (user_id=%s)...", user.id)
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email, "user_id": user.id},
            expires_delta=access_token_expires
        )
        refresh_token = create_refresh_token(
            data={"sub": user.email, "user_id": user.id}
        )
        logger.info("[Auth] login: tokens générés")
    except Exception as e:
        logger.exception("[Auth] login: erreur lors de la création des tokens: %s", e)
        raise

    try:
        logger.info("[Auth] login: sauvegarde du refresh token...")
        save_refresh_token(db, user.id, refresh_token)
        logger.info("[Auth] login: refresh token sauvegardé, succès")
    except Exception as e:
        logger.exception("[Auth] login: erreur lors de save_refresh_token: %s", e)
        raise

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token)
def refresh_token(token_request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Renouvelle l'access token à partir d'un refresh token"""
    # Vérifier le refresh token
    token_data = verify_token(token_request.refresh_token, token_type="refresh")
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalide"
        )
    
    # Vérifier que le token existe en base de données
    db_refresh_token = get_refresh_token(db, token_request.refresh_token)
    if not db_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalide ou expiré"
        )
    
    # Récupérer l'utilisateur
    user = get_user_by_id(db, user_id=token_data.user_id) if token_data.user_id else None
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable ou inactif"
        )
    
    # Générer un nouveau access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "refresh_token": token_request.refresh_token,  # Le refresh token reste le même
        "token_type": "bearer"
    }


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(token_request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Déconnexion : invalide le refresh token"""
    deleted = delete_refresh_token(db, token_request.refresh_token)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refresh token introuvable"
        )
    
    return {"message": "Déconnexion réussie"}
