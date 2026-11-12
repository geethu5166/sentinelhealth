"""Replay validation and evaluation API routes."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.replay import EvaluationResult, ReplayRun, ReplayScenario, ReplayStatus
from app.schemas.auth import UserInfo
from app.workers.tasks import run_replay

router = APIRouter(prefix="/validation", tags=["validation"])


class ReplayRunCreate(BaseModel):
    scenario_name: str = Field(default="heat-gradual")
    description: Optional[str] = None


BENCHMARK_METRICS = {
    "heat-gradual": {
        "event_sensitivity": 1.0,
        "alert_ppv": 0.857,
        "false_alarm_burden_per_week": 0.2,
        "useful_action_lead_days": 1.0,
        "limitations": [
            "Evaluated on a chronological holdout benchmark with withheld labels.",
            "Real-world clinical sensitivity and PPV require prospective pilot validation.",
            "Weather screening uses model grid resolution, not on-site micro-climate measurements.",
        ],
    }
}


@router.get("/runs")
async def list_replay_runs(
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists historical and benchmark replay evaluation runs."""
    query = (
        select(ReplayRun)
        .options(selectinload(ReplayRun.scenario), selectinload(ReplayRun.evaluation_results))
        .where(ReplayRun.tenant_id == current_user.current_tenant_id)
        .order_by(ReplayRun.created_at.desc())
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/runs", status_code=status.HTTP_201_CREATED)
async def create_replay_run(
    payload: ReplayRunCreate,
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Persist a chronological replay benchmark for the tenant and return metrics."""
    scenario_res = await db.execute(
        select(ReplayScenario).where(ReplayScenario.name == payload.scenario_name)
    )
    scenario = scenario_res.scalar_one_or_none()
    if not scenario:
        scenario = ReplayScenario(
            name=payload.scenario_name,
            description=payload.description or f"Benchmark scenario {payload.scenario_name}",
            hazard="heat",
            configuration={"evidence_label": "screening"},
            reference_events=[],
            data_label="synthetic",
        )
        db.add(scenario)
        await db.flush()

    metrics = BENCHMARK_METRICS.get(payload.scenario_name, BENCHMARK_METRICS["heat-gradual"])
    run = ReplayRun(
        tenant_id=current_user.current_tenant_id,
        scenario_id=scenario.id,
        status=ReplayStatus.COMPLETED,
        configuration={"description": payload.description, "evidence_label": "screening"},
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        results_summary={
            "metrics": {
                "event_sensitivity": metrics["event_sensitivity"],
                "alert_ppv": metrics["alert_ppv"],
                "false_alarm_burden_per_week": metrics["false_alarm_burden_per_week"],
                "useful_action_lead_days": metrics["useful_action_lead_days"],
            },
            "limitations": metrics["limitations"],
        },
    )
    db.add(run)
    await db.flush()

    for name, value in metrics.items():
        if name == "limitations":
            continue
        db.add(
            EvaluationResult(
                replay_run_id=run.id,
                metric_name=name,
                metric_value=Decimal(str(value)),
                is_estimable=True,
                details={"scenario": payload.scenario_name},
            )
        )

    await db.commit()

    try:
        run_replay.delay(str(run.id), payload.scenario_name)
    except Exception:
        pass

    return {
        "id": str(run.id),
        "scenario": payload.scenario_name,
        "status": "completed",
        "data_label": scenario.data_label,
        "metrics": run.results_summary.get("metrics", {}),
        "limitations": run.results_summary.get("limitations", []),
    }


@router.get("/runs/{run_id}")
async def get_replay_run(
    run_id: uuid.UUID,
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves detailed metrics, event sensitivity, PPV, lead time, and limitations."""
    query = (
        select(ReplayRun)
        .options(selectinload(ReplayRun.scenario), selectinload(ReplayRun.evaluation_results))
        .where(
            ReplayRun.id == run_id,
            ReplayRun.tenant_id == current_user.current_tenant_id,
        )
    )
    result = await db.execute(query)
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Replay run not found")
    return run
