"""Celery application configuration."""

import os
from celery import Celery

REDIS_URL = os.getenv("SENTINEL_REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "sentinelhealth",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "periodic-detection-run": {
            "task": "app.workers.tasks.scheduled_surveillance_sweep",
            "schedule": 300.0,  # every 5 minutes
        },
    },
)

