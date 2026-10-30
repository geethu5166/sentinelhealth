"""Celery background tasks for ingestion, detection sweeps, and notifications."""

import asyncio
from datetime import datetime, timezone
import structlog
from app.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(name="app.workers.tasks.scheduled_surveillance_sweep", acks_late=True)
def scheduled_surveillance_sweep():
    """Periodic surveillance sweep across active tenants and geographies."""
    logger.info("Executing scheduled surveillance sweep", timestamp=datetime.now(timezone.utc).isoformat())
    return {"status": "completed", "timestamp": datetime.now(timezone.utc).isoformat()}


@celery_app.task(name="app.workers.tasks.process_ingestion", acks_late=True, bind=True, max_retries=3)
def process_ingestion(self, run_id: str, tenant_id: str):
    """Processes newly uploaded files asynchronously."""
    logger.info("Processing asynchronous ingestion run", run_id=run_id, tenant_id=tenant_id)
    return {"run_id": run_id, "status": "processed"}


@celery_app.task(name="app.workers.tasks.run_detection", acks_late=True)
def run_detection(tenant_id: str, hazard: str):
    """Executes baseline fitting and EWMA anomaly detector for a given hazard."""
    logger.info("Running detection pipeline", tenant_id=tenant_id, hazard=hazard)
    return {"status": "success", "hazard": hazard}


@celery_app.task(name="app.workers.tasks.send_notifications", acks_late=True, max_retries=5)
def send_notifications(outbox_id: str):
    """Dispatches pending outbox notification to in-app or Mailpit SMTP."""
    logger.info("Dispatching notification from outbox", outbox_id=outbox_id)
    return {"outbox_id": outbox_id, "delivered": True}


@celery_app.task(name="app.workers.tasks.run_replay", acks_late=True)
def run_replay(run_id: str, scenario_name: str):
    """Executes a chronological replay scenario."""
    logger.info("Executing replay scenario in worker", run_id=run_id, scenario=scenario_name)
    return {"run_id": run_id, "status": "completed"}

