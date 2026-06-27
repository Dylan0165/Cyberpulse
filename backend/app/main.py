"""AutoPentest AI — FastAPI application entry point."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import engine, Base
from app.api.endpoints import (
    targets,
    scans,
    legal,
    users,
    reports,
    websocket,
    tools,
    scanner,
    stats,
    settings as settings_routes,
    auth,
    notifications,
    schedule,
    billing,
    admin,
    agents,
    projects,
    findings,
    api_keys,
    teams,
    analytics,
    demo,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.warning(f"Database not available at startup (running without DB): {e}")
    yield
    await engine.dispose()


app = FastAPI(
    title="AutoPentest AI",
    description="AI-powered penetration testing SaaS platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS — explicit allowlist so credentialed (cookie) cross-origin requests from
# the marketing site (scanix.nl) reach the dashboard API (app.scanix.nl).
# NOTE: a wildcard origin ("*") is invalid together with allow_credentials=True;
# the browser requires the exact origin echoed back, which CORSMiddleware does.
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3100",
    "http://192.168.121.40",
    "http://192.168.121.40:3000",
    "http://192.168.121.40:3100",
    "https://scanix.nl",
    "https://www.scanix.nl",
    "https://app.scanix.nl",
]

# Extra origins can be added at deploy time without a code change.
_extra = os.getenv("EXTRA_CORS_ORIGINS", "")
if _extra:
    ALLOWED_ORIGINS.extend(o.strip() for o in _extra.split(",") if o.strip())

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,  # required so the browser sends/accepts cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

# Per-IP request rate limiting (slowapi). Decorators live on sensitive endpoints.
try:
    from app.core.ratelimit import limiter, SLOWAPI_AVAILABLE
    if SLOWAPI_AVAILABLE:
        from slowapi import _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        logger.info("Rate limiting enabled (slowapi)")
except Exception as exc:
    logger.warning("Rate limiting not enabled: %s", exc)

# API Routes
app.include_router(users.router, prefix="/api")
app.include_router(targets.router, prefix="/api")
app.include_router(scans.router, prefix="/api")
app.include_router(legal.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(tools.router, prefix="/api")
app.include_router(scanner.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(settings_routes.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(schedule.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(findings.router, prefix="/api")
app.include_router(api_keys.router, prefix="/api")
app.include_router(teams.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(demo.router, prefix="/api")

# WebSocket Routes
app.include_router(websocket.router)


# ── Scanix Agent distribution (install script + agent source) ─────────────────
# Served unauthenticated so `curl | bash` installs work; the agent itself only
# does anything with a valid AGENT_TOKEN.
import os as _os
from fastapi.responses import FileResponse, PlainTextResponse


def _resolve_agent_dir() -> str:
    """Locate the agent/ files. The backend image is built from ./backend, so the
    repo-root /agent isn't inside it — in containers it's mounted at /srv/agent
    (AGENT_FILES_DIR). Falls back to the repo path for local/dev runs."""
    candidates = [
        _os.getenv("AGENT_FILES_DIR"),
        "/srv/agent",
        _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(__file__))), "agent"),
    ]
    for c in candidates:
        if c and _os.path.exists(_os.path.join(c, "install.sh")):
            return c
    return candidates[-1]


_AGENT_DIR = _resolve_agent_dir()


@app.get("/agent/install.sh")
async def agent_install_script():
    path = _os.path.join(_AGENT_DIR, "install.sh")
    if not _os.path.exists(path):
        return PlainTextResponse("# Scanix agent installer not found\n", status_code=404)
    return FileResponse(path, media_type="text/x-shellscript", filename="install.sh")


@app.get("/agent/scanix_agent.py")
async def agent_source():
    path = _os.path.join(_AGENT_DIR, "scanix_agent.py")
    if not _os.path.exists(path):
        return PlainTextResponse("# Scanix agent not found\n", status_code=404)
    return FileResponse(path, media_type="text/x-python", filename="scanix_agent.py")


@app.get("/api/health")
async def health_check():
    """Liveness + dependency check (DB + Redis). Never raises."""
    db_ok = False
    redis_ok = False
    try:
        from sqlalchemy import text
        from app.core.database import async_session
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    try:
        from app.core.redis import get_redis
        rc = await get_redis()
        await rc.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    return {
        "status": "healthy" if (db_ok and redis_ok) else "degraded",
        "service": "autopentest-ai",
        "database": "ok" if db_ok else "error",
        "redis": "ok" if redis_ok else "error",
        "version": "1.0.0",
    }
