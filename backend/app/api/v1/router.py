"""Root API v1 router combining all resource endpoints."""

from fastapi import APIRouter

from app.api.v1.alerts import router as alerts_router
from app.api.v1.analytics_routes import router as analytics_router
from app.api.v1.audit import router as audit_router
from app.api.v1.auth_routes import router as auth_router
from app.api.v1.exports import router as exports_router
from app.api.v1.geographies import router as geographies_router
from app.api.v1.health import router as health_router
from app.api.v1.ingestions import router as ingestions_router
from app.api.v1.overview import router as overview_router
from app.api.v1.playbooks import router as playbooks_router
from app.api.v1.signals import router as signals_router
from app.api.v1.sources import router as sources_router
from app.api.v1.tasks_routes import router as tasks_router
from app.api.v1.validation import router as validation_router

api_router = APIRouter()

# Health endpoints at root level of API v1
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(overview_router)
api_router.include_router(geographies_router)
api_router.include_router(sources_router)
api_router.include_router(signals_router)
api_router.include_router(ingestions_router)
api_router.include_router(alerts_router)
api_router.include_router(tasks_router)
api_router.include_router(playbooks_router)
api_router.include_router(validation_router)
api_router.include_router(exports_router)
api_router.include_router(audit_router)
api_router.include_router(analytics_router)

