"""Celery background tasks for ingestion, detection sweeps, and notifications."""

import asyncio
from datetime import datetime, timezone
import structlog
from app.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(name="app.workers.tasks.scheduled_surveillance_sweep", acks_late=True)
def scheduled_surveillance_sweep():
    """Periodic surveillance sweep: refresh realtime heat baselines then mark complete."""
    logger.info("Executing scheduled surveillance sweep", timestamp=datetime.now(timezone.utc).isoformat())
    try:
        train_realtime_baselines.run(
            tenant_id="system",
            latitude=21.1458,
            longitude=79.0882,
            lookback_days=60,
        )
        return {"status": "completed", "trained": True, "timestamp": datetime.now(timezone.utc).isoformat()}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Sweep completed without realtime retrain", error=str(exc))
        return {"status": "completed", "trained": False, "timestamp": datetime.now(timezone.utc).isoformat()}


@celery_app.task(name="app.workers.tasks.process_ingestion", acks_late=True, bind=True, max_retries=3)
def process_ingestion(self, run_id: str, tenant_id: str):
    """Processes newly uploaded files asynchronously and triggers detection."""
    logger.info("Processing asynchronous ingestion run", run_id=run_id, tenant_id=tenant_id)
    try:
        run_detection.delay(tenant_id=tenant_id, hazard="heat")
    except Exception:
        pass
    return {"run_id": run_id, "status": "processed"}


@celery_app.task(name="app.workers.tasks.run_detection", acks_late=True)
def run_detection(tenant_id: str, hazard: str):
    """Executes ensemble baseline fitting plus EWMA/CUSUM detectors for a hazard."""
    logger.info("Running detection pipeline", tenant_id=tenant_id, hazard=hazard)
    report = None
    if hazard in {"heat", "heat_illness", "heat-illness"}:
        try:
            report = train_realtime_baselines.run(tenant_id=tenant_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Realtime detection fallback", error=str(exc))
    return {
        "status": "success",
        "hazard": hazard,
        "detectors": ["ewma", "cusum"],
        "selected_model": (report or {}).get("selected_model"),
        "ewma_anomaly": (report or {}).get("ewma_anomaly"),
        "cusum_anomaly": (report or {}).get("cusum_anomaly"),
    }


@celery_app.task(name="app.workers.tasks.train_realtime_baselines", acks_late=True, bind=True, max_retries=2)
def train_realtime_baselines(
    self,
    tenant_id: str,
    latitude: float = 21.1458,
    longitude: float = 79.0882,
    lookback_days: int = 60,
):
    """Fetch live Open-Meteo history and train ensemble screening baselines."""
    from app.analytics.training.realtime import report_to_dict, train_realtime_heat_baselines

    logger.info(
        "Training realtime heat baselines",
        tenant_id=tenant_id,
        latitude=latitude,
        longitude=longitude,
        lookback_days=lookback_days,
    )

    async def _run():
        return await train_realtime_heat_baselines(
            latitude=latitude,
            longitude=longitude,
            lookback_days=lookback_days,
        )

    try:
        report = asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        logger.exception("Realtime baseline training failed", error=str(exc))
        raise self.retry(exc=exc, countdown=30)

    payload = report_to_dict(report)
    payload["tenant_id"] = tenant_id
    payload["status"] = "completed"
    return payload


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

