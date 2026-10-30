"""Audit events query endpoint for privacy officers and auditors."""

from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.privacy import AuditEvent
from app.schemas.auth import UserInfo

router = APIRouter(prefix="/audit-events", tags=["audit"])


@router.get("", dependencies=[Depends(require_role(["privacy_officer", "platform_admin"]))])
async def list_audit_events(
    limit: int = Query(default=50, le=100),
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists append-only tenant audit events for governance reviews."""
    query = (
        select(AuditEvent)
        .where(AuditEvent.tenant_id == current_user.current_tenant_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    events = result.scalars().all()
    return events

