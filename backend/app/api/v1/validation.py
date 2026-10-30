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

