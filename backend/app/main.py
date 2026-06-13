"""AutoPentest AI — FastAPI application entry point."""

import logging
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

# CORS — allow all origins (school project on closed netlab, no public exposure)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# WebSocket Routes
app.include_router(websocket.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "autopentest-ai"}
