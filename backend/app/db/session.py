from collections.abc import AsyncGenerator
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

# Lazy initialization pour éviter l'erreur si asyncpg n'est pas installé
_engine: Optional[AsyncEngine] = None
_AsyncSessionLocal: Optional[async_sessionmaker] = None


def _get_engine():
    """Crée l'engine asynchrone de manière paresseuse"""
    global _engine, _AsyncSessionLocal
    if _engine is None:
        # Convertir postgresql:// en postgresql+asyncpg:// si nécessaire
        database_url = settings.database_url
        if database_url.startswith("postgresql://") and "+asyncpg" not in database_url:
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        _engine = create_async_engine(database_url, echo=False, future=True)
        _AsyncSessionLocal = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_AsyncSessionLocal():
    """Obtient l'AsyncSessionLocal (initialise l'engine si nécessaire)"""
    _get_engine()  # S'assure que l'engine est créé
    if _AsyncSessionLocal is None:
        raise RuntimeError("AsyncSessionLocal n'a pas été initialisé")
    return _AsyncSessionLocal


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Obtient une session asynchrone"""
    _get_engine()  # S'assure que l'engine est créé
    async with _AsyncSessionLocal() as session:
        yield session
