"""Analytics training and model inspection endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.analytics.training.realtime import report_to_dict, train_realtime_heat_baselines
from app.auth.dependencies import get_current_user
from app.schemas.auth import UserInfo
from app.workers.tasks import train_realtime_baselines

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/train/realtime")
async def train_realtime(
    latitude: float = Query(21.1458, description="Training latitude (default Central India)"),
    longitude: float = Query(79.0882, description="Training longitude"),
    lookback_days: int = Query(60, ge=21, le=120),
    async_worker: bool = Query(False, description="Enqueue Celery worker instead of inline train"),
    current_user: UserInfo = Depends(get_current_user),
):
    """Train ensemble screening baselines on live Open-Meteo history for the operator tenant."""
    if async_worker:
        task = train_realtime_baselines.delay(
            tenant_id=str(current_user.current_tenant_id),
            latitude=latitude,
            longitude=longitude,
            lookback_days=lookback_days,
        )
        return {"status": "queued", "task_id": task.id, "evidence_label": "screening"}

    try:
        report = await train_realtime_heat_baselines(
            latitude=latitude,
            longitude=longitude,
            lookback_days=lookback_days,
        )
    except Exception as exc:  # noqa: BLE001 — surface upstream connector failures cleanly
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Realtime training failed: {exc}",
        ) from exc

    payload = report_to_dict(report)
    payload["tenant_id"] = str(current_user.current_tenant_id)
    payload["status"] = "completed"
    return payload


@router.get("/detectors")
async def list_detectors(current_user: UserInfo = Depends(get_current_user)):
    """Describe active screening detectors available to the console."""
    _ = current_user
    return {
        "evidence_label": "screening",
        "baselines": [
            "recent_history_weekday_matched",
            "poisson_glm",
            "negative_binomial_glm",
            "quasi_poisson_glm",
            "seasonal_ema",
            "ensemble_holdout_mae",
        ],
        "detectors": [
            {"name": "NIST-signed-EWMA", "role": "upper-tail residual smoothing"},
            {"name": "one-sided-CUSUM", "role": "sustained residual elevation"},
        ],
        "realtime_source": "Open-Meteo archive/forecast",
    }
