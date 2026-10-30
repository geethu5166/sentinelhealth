"""Audit logging service."""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.privacy import AuditEvent


async def log_audit_event(
    session: AsyncSession,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    tenant_id: Optional[uuid.UUID] = None,
    actor_id: Optional[uuid.UUID] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> AuditEvent:
    """Creates and persists an immutable audit event entry."""
    event = AuditEvent(
        tenant_id=tenant_id,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None,
        details=details or {},
        ip_address=ip_address,
    )
    session.add(event)
    await session.flush()
    return event

