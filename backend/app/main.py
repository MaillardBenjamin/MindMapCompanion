import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import OperationalError, ProgrammingError
from app.api.routes import auth, users, mindmaps, nodes, triggers, actions, weather
from app.routers import agents
from app.routers import configurable_agents
from app.routers import admin
from app.routers import history
from app.routers import settings as settings_router
from app.routers import actions as actions_router
from app.mcp.web_search_server import router as web_search_mcp_router
from app.config import settings
from app.services.scheduler import load_cron_triggers, start_scheduler

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Désactiver les logs d'accès HTTP d'uvicorn
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

app = FastAPI(
    title="Personal Assistant API",
    description="API REST avec authentification JWT pour Personal Assistant",
    version="1.0.0"
)

# Configuration CORS depuis les variables d'environnement
# Le field_validator dans Settings.parse_cors_origins convertit déjà la string en liste
cors_origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [str(settings.CORS_ORIGINS)]
cors_methods = settings.CORS_ALLOW_METHODS if isinstance(settings.CORS_ALLOW_METHODS, list) else ["*"]
cors_headers = settings.CORS_ALLOW_HEADERS if isinstance(settings.CORS_ALLOW_HEADERS, list) else ["*"]

logger.info(f"🌐 Configuration CORS - Origines autorisées: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=cors_methods,
    allow_headers=cors_headers,
)

# Gestionnaire d'exception global pour s'assurer que les en-têtes CORS sont toujours envoyés
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Gestionnaire d'exception global qui garantit l'envoi des en-têtes CORS"""
    logger.error(f"❌ Erreur non gérée: {exc}", exc_info=True)
    
    # Déterminer l'origine autorisée
    origin = request.headers.get("origin")
    allowed_origin = origin if origin in cors_origins else cors_origins[0] if cors_origins else "*"
    
    # Vérifier si c'est une erreur de base de données (colonne manquante)
    if isinstance(exc, (OperationalError, ProgrammingError)):
        error_msg = str(exc)
        if "input_schema" in error_msg or "column" in error_msg.lower() or "does not exist" in error_msg.lower():
            logger.error("⚠️ Colonne manquante en base de données. Exécutez la migration: alembic upgrade head")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "Erreur de base de données. La colonne 'input_schema' est peut-être manquante. Exécutez: alembic upgrade head"
                },
                headers={
                    "Access-Control-Allow-Origin": allowed_origin,
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Allow-Methods": ",".join(cors_methods) if isinstance(cors_methods, list) else "*",
                    "Access-Control-Allow-Headers": ",".join(cors_headers) if isinstance(cors_headers, list) else "*",
                }
            )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Erreur interne du serveur: {str(exc)}"},
        headers={
            "Access-Control-Allow-Origin": allowed_origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": ",".join(cors_methods) if isinstance(cors_methods, list) else "*",
            "Access-Control-Allow-Headers": ",".join(cors_headers) if isinstance(cors_headers, list) else "*",
        }
    )

# Inclusion des routes
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(mindmaps.router)
app.include_router(nodes.router)
app.include_router(triggers.router)
app.include_router(weather.router)
app.include_router(actions.router)  # Actions liées aux triggers (ancien système)
app.include_router(actions_router.router)  # Actions liées aux nœuds (nouveau système)
app.include_router(agents.router, prefix="/api")
app.include_router(configurable_agents.router, prefix="/api")
app.include_router(admin.router)
app.include_router(history.router)
app.include_router(settings_router.router)
app.include_router(web_search_mcp_router, prefix="/api")


@app.get("/")
def root():
    """Point d'entrée de l'API"""
    return {"message": "Personal Assistant API", "version": "1.0.0"}


@app.get("/health")
def health_check():
    """Vérification de l'état de l'API"""
    return {"status": "healthy"}


def _health_check_db_impl():
    """
    Diagnostic de la base de données : connexion, table users, colonnes agent_*.
    Utile pour vérifier que la migration a bien été appliquée.
    """
    from app.database import engine
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError, ProgrammingError

    result = {"status": "unknown", "checks": {}}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        result["checks"]["connection"] = "ok"
    except Exception as e:
        result["checks"]["connection"] = f"error: {type(e).__name__}: {str(e)[:200]}"
        result["status"] = "error"
        result["detail"] = "Impossible de se connecter à la base. Vérifiez DATABASE_URL et que PostgreSQL tourne."
        return result

    try:
        with engine.connect() as conn:
            row = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users' ORDER BY ordinal_position")).fetchall()
        columns = [r[0] for r in row] if row else []
        result["checks"]["users_columns"] = columns
        required = ["id", "email", "hashed_password", "agent_langue", "agent_adresse", "agent_prenom", "agent_ton"]
        missing = [c for c in required if c not in columns]
        if missing:
            result["checks"]["missing_columns"] = missing
            result["status"] = "schema_outdated"
            result["detail"] = f"Colonnes manquantes dans users: {missing}. Exécutez: cd backend && alembic upgrade head"
        else:
            result["checks"]["schema"] = "ok"
            result["status"] = "healthy"
    except (OperationalError, ProgrammingError) as e:
        result["checks"]["schema"] = f"error: {str(e)[:200]}"
        result["status"] = "error"
        result["detail"] = str(e)
    except Exception as e:
        result["checks"]["schema"] = f"error: {type(e).__name__}: {str(e)[:200]}"
        result["status"] = "error"
        result["detail"] = str(e)

    return result


@app.get("/health/db")
def health_check_db():
    """Diagnostic base de données (voir /api/health/db)."""
    return _health_check_db_impl()


@app.get("/api/health/db")
def health_check_db_api():
    """Diagnostic base de données : connexion, table users, colonnes agent_*."""
    return _health_check_db_impl()


@app.get("/api/test-cors")
def test_cors():
    """Endpoint de test pour vérifier que CORS fonctionne"""
    return {"message": "CORS is working", "cors_origins": cors_origins}


# Démarrer le scheduler au démarrage de l'application
@app.on_event("startup")
async def startup_event():
    """Démarre le scheduler au démarrage de l'application"""
    logger.info("🚀 Démarrage du scheduler...")
    scheduler = start_scheduler()
    app.state.scheduler = scheduler
    await load_cron_triggers(scheduler)
    logger.info("✅ Scheduler démarré (triggers cron chargés)")


@app.on_event("shutdown")
async def shutdown_event():
    """Arrête le scheduler à l'arrêt de l'application"""
    if hasattr(app.state, "scheduler"):
        logger.info("🛑 Arrêt du scheduler...")
        app.state.scheduler.shutdown()
        logger.info("✅ Scheduler arrêté")
