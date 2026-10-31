"""Replay validation and evaluation API routes."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.replay import EvaluationResult, ReplayRun, ReplayScenario, ReplayStatus
from app.schemas.auth import UserInfo

router = APIRouter(prefix="/validation", tags=["validation"])


class ReplayRunCreate(BaseModel):
    scenario_name: str
    description: Optional[str] = None


@router.get("/runs")
async def list_replay_runs(
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists historical and synthetic replay evaluation runs."""
    query = (
        select(ReplayRun)
        .options(selectinload(ReplayRun.scenario), selectinload(ReplayRun.evaluation_results))
        .where(ReplayRun.tenant_id == current_user.current_tenant_id)
        .order_by(ReplayRun.created_at.desc())
    )
    result = await db.execute(query)
    runs = result.scalars().all()
    return runs


@router.get("/summary")
async def get_replay_summary(
    current_user: UserInfo = Depends(get_current_user),
):
    """Retrieves the full Phase 4 CDC-aligned replay evaluation summary across 15 benchmark scenarios."""
    import json
    from pathlib import Path

    summary_file = Path(__file__).resolve().parent.parent.parent.parent / "fixtures" / "replay_evaluation_summary.json"
    if not summary_file.exists():
        # Fallback to backend/fixtures
        summary_file = Path("fixtures/replay_evaluation_summary.json")

    if not summary_file.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Replay evaluation summary not generated")

    with open(summary_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Attach multiseed summary if present
    ms_file = summary_file.parent / "replay_evaluation_multiseed.json"
    if ms_file.exists():
        with open(ms_file, "r", encoding="utf-8") as f:
            data["multiseed_summary"] = json.load(f)

    return data


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

