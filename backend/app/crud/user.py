import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
from app.models.user import User, RefreshToken
from app.schemas.user import UserCreate
from app.auth.password import get_password_hash
from app.config import settings

logger = logging.getLogger(__name__)


def get_user_by_email(db: Session, email: str) -> User | None:
    """Récupère un utilisateur par son email"""
    logger.info("[CRUD User] get_user_by_email: email=%s", email)
    try:
        q = db.query(User).filter(User.email == email)
        logger.info("[CRUD User] get_user_by_email: exécution query...")
        user = q.first()
        logger.info("[CRUD User] get_user_by_email: ok, user_id=%s", user.id if user else None)
        return user
    except Exception as e:
        logger.exception("[CRUD User] get_user_by_email: erreur %s", e)
        raise


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Récupère un utilisateur par son ID"""
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, user: UserCreate) -> User:
    """Crée un nouvel utilisateur"""
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def save_refresh_token(db: Session, user_id: int, token: str) -> RefreshToken:
    """Sauvegarde un refresh token en base de données"""
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db_token = RefreshToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at
    )
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return db_token


def get_refresh_token(db: Session, token: str) -> RefreshToken | None:
    """Récupère un refresh token valide"""
    return db.query(RefreshToken).filter(
        and_(
            RefreshToken.token == token,
            RefreshToken.expires_at > datetime.utcnow()
        )
    ).first()


def delete_refresh_token(db: Session, token: str) -> bool:
    """Supprime un refresh token"""
    db_token = db.query(RefreshToken).filter(RefreshToken.token == token).first()
    if db_token:
        db.delete(db_token)
        db.commit()
        return True
    return False


def delete_all_user_refresh_tokens(db: Session, user_id: int) -> None:
    """Supprime tous les refresh tokens d'un utilisateur"""
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
    db.commit()
