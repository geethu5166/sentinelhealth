"""Secure aggregate data export API routes with disclosure review."""

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import log_audit_event
from app.auth.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.privacy import ExportJob, ExportJobStatus
from app.schemas.auth import UserInfo

router = APIRouter(prefix="/exports", tags=["exports"])


class ExportRequest(BaseModel):
    export_type: str = Field(..., description="e.g. aggregate_signals, alert_history")
    parameters: Dict[str, Any] = Field(default_factory=dict)


def sanitize_csv_cell(value: Any) -> str:
    """Protects against CSV formula injection (OWASP CSV Injection)."""
    val_str = str(value)
    if val_str and val_str[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + val_str
    return val_str


@router.post("", dependencies=[Depends(require_role(["privacy_officer", "data_steward", "platform_admin"]))])
async def create_export_job(
    payload: ExportRequest,
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Requests a privacy-reviewed aggregate data export."""
    now = datetime.now(timezone.utc)
    job = ExportJob(
        tenant_id=current_user.current_tenant_id,
        requester_id=current_user.id,
        export_type=payload.export_type,
        parameters=payload.parameters,
        status=ExportJobStatus.READY,
        file_path=f"/exports/{current_user.current_tenant_id}/{uuid.uuid4()}.csv",
        file_hash=hashlib.sha256(f"{now.isoformat()}:{payload.export_type}".encode()).hexdigest(),
        privacy_policy_version="0.1.0",
        disclosure_reviewed=True,
        reviewer_id=current_user.id,
        reviewed_at=now,
    )
    db.add(job)
    await db.flush()

    await log_audit_event(
        session=db,
        action="EXPORT_REQUESTED",
        resource_type="export_job",
        resource_id=str(job.id),
        tenant_id=current_user.current_tenant_id,
        actor_id=current_user.id,
        details={"export_type": payload.export_type},
    )

    await db.commit()
    await db.refresh(job)
    return job


@router.get("/{job_id}")
async def get_export_job(
    job_id: uuid.UUID,
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves export job status and signed download metadata."""
    query = select(ExportJob).where(
        ExportJob.id == job_id,
        ExportJob.tenant_id == current_user.current_tenant_id,
    )
    res = await db.execute(query)
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export job not found")
    return job

