"""VELOOP Rewards - Referral System API (FastAPI)."""
import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, ads, auth, health, referrals
from app.core.config import settings
from app.core.errors import register_exception_handlers

logging.basicConfig(
    level=logging.INFO,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger("veloop")

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description=(
        "Backend for the VELOOP Rewards referral program: attribution, "
        "milestone rewards, reward ledger and anti-fraud protection.\n\n"
        "**Principle:** the frontend is never the source of truth."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ---- CORS: explicit allowlist only (never "*" for credentialed APIs) ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Device-Signals", "X-Device-Token", "Idempotency-Key"],
    max_age=600,
)


@app.middleware("http")
async def security_and_logging(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    started = time.perf_counter()
    response = await call_next(request)
    duration = (time.perf_counter() - started) * 1000

    response.headers["X-Request-Id"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Cache-Control"] = "no-store"
    if settings.ENV != "development":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    logger.info(
        "%s %s %s %.1fms rid=%s",
        request.method, request.url.path, response.status_code, duration, request_id,
    )
    return response


register_exception_handlers(app)

app.include_router(health.router, prefix=settings.API_PREFIX)
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(referrals.router, prefix=settings.API_PREFIX)
app.include_router(ads.router, prefix=settings.API_PREFIX)
app.include_router(admin.router, prefix=settings.API_PREFIX)


@app.on_event("startup")
def on_startup() -> None:
    from app.db.base import Base, engine
    from app.db.seed import seed_milestones

    if settings.is_sqlite or settings.ENV == "development":
        # Production uses Alembic migrations; this keeps local/dev friction low.
        Base.metadata.create_all(engine)
    seed_milestones()
    logger.info("VELOOP referral API started (env=%s)", settings.ENV)


@app.get("/")
def root():
    return {"success": True, "data": {"service": settings.APP_NAME, "docs": "/docs"}}
