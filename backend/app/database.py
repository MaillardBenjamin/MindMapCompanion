from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Timeouts pour éviter les blocages (ex. lock en base pendant une migration)
_connect_args = {}
if "postgresql" in settings.DATABASE_URL and "asyncpg" not in settings.DATABASE_URL:
    _connect_args["connect_timeout"] = 10  # psycopg2

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,
)


@event.listens_for(engine, "connect")
def _set_statement_timeout(dbapi_conn, connection_record):
    """Abandonner les requêtes qui dépassent 15 s (évite blocage infini)."""
    try:
        cursor = dbapi_conn.cursor()
        cursor.execute("SET statement_timeout = 15000")  # 15 secondes
        cursor.close()
    except Exception:
        pass  # Ignorer si le driver ne supporte pas (ex. SQLite)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency pour obtenir une session de base de données"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
