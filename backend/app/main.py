"""Main FastAPI application entry point for SentinelHealth."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.api.v1.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure connection pool is initialized
    yield
    # Shutdown: dispose of database engine
    await engine.dispose()


app = FastAPI(
    title="SentinelHealth API",
    description="Population and Workforce Health Early Warning Platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health routes at root for Docker/K8s probes
app.include_router(health_router)

# Mount API v1
app.include_router(api_router, prefix="/api/v1")

# Mount Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/")
async def root():
    return {
        "service": "SentinelHealth Population and Workforce Health Early Warning",
        "version": "0.2.0",
        "demo_mode": settings.DEMO_MODE,
        "evidence_label": "screening",
        "disclaimer": "Screening decision support only. Not a clinical diagnosis tool and not for individual medical or punitive use.",
        "docs": "/docs",
        "analytics": "/api/v1/analytics/detectors",
    }

