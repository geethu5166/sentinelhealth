"""Health and readiness check endpoints."""

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.core.config import settings
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def liveness():
    """Liveness probe: verifies process is responding."""
    return {"status": "ok", "service": "sentinelhealth-api"}


@router.get("/health/ready")
async def readiness(db: AsyncSession = Depends(get_db)):
    """Readiness probe: verifies PostgreSQL and Redis connections."""
    checks = {"database": False, "redis": False}

    # Check Database
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        checks["database_error"] = str(e)

    # Check Redis
    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_timeout=2.0)
        await r.ping()
        await r.aclose()
        checks["redis"] = True
    except Exception as e:
        checks["redis_error"] = str(e)

    all_ready = checks["database"] and checks["redis"]
    status_code = status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={"status": "ready" if all_ready else "degraded", "checks": checks},
    )

