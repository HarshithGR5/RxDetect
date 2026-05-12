"""
main.py
FastAPI application entrypoint.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.config import settings
from app.api.v1 import auth, patients, prescriptions, reports

log = structlog.get_logger(__name__)

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="AI-powered prescription discrepancy detection API",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
_dev_domain = os.environ.get("REPLIT_DEV_DOMAIN", "")
_allowed_origins = [
    "http://localhost:3000",
    "http://0.0.0.0:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5000",
    "http://0.0.0.0:5000",
    "http://127.0.0.1:5000",
    "https://rx-detect.vercel.app",
]
if _dev_domain:
    _allowed_origins += [
        f"https://{_dev_domain}",
        f"https://3000-{_dev_domain}",
        f"https://5000-{_dev_domain}",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"https://.*\.(vercel\.app|replit\.dev)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
PREFIX = "/api/v1"

app.include_router(auth.router,          prefix=f"{PREFIX}/auth",          tags=["Auth"])
app.include_router(patients.router,      prefix=f"{PREFIX}/patients",       tags=["Patients"])
app.include_router(prescriptions.router, prefix=f"{PREFIX}/prescriptions",  tags=["Prescriptions"])
app.include_router(reports.router,       prefix=f"{PREFIX}/reports",        tags=["Reports"])


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    log.info("startup.begin", app=settings.app_name)

    # Create all DB tables (in production, use Alembic migrations instead)
    from app.dependencies import engine
    from app.models import Base
    Base.metadata.create_all(bind=engine)
    log.info("startup.db_tables_ready")

    # Load FAISS knowledge base ONLY if empty
    try:
        from app.services.rag.vector_store import get_vector_store
        from app.services.rag.knowledge_loader import load_from_directory

        store = get_vector_store()

        if store.total_vectors() == 0:
            log.info("startup.loading_knowledge_base")
            load_from_directory()
        else:
            log.info("startup.knowledge_base_already_loaded", total=store.total_vectors())

    except Exception as e:
        log.warning("startup.knowledge_base_failed", error=str(e))

    if settings.sentry_dsn:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        sentry_sdk.init(dsn=settings.sentry_dsn, integrations=[FastApiIntegration()])
        log.info("startup.sentry_configured")

    log.info("startup.complete")


@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.app_name}


@app.get("/")
def root():
    return {"message": f"Welcome to {settings.app_name}. Visit /docs for the API reference."}
