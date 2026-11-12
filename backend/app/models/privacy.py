"""Privacy, disclosure control, export jobs, and audit event models."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin, pg_enum

__all__ = [
    "DisclosureDecisionStatus",
    "ExportJobStatus",
    "PrivacyPolicy",
    "DisclosureDecision",
    "ExportJob",
    "AuditEvent",
]


class DisclosureDecisionStatus(str, enum.Enum):
    APPROVED = "approved"
    DENIED = "denied"
    PARTIAL = "partial"


class ExportJobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    DOWNLOADED = "downloaded"
    EXPIRED = "expired"
    DENIED = "denied"


class PrivacyPolicy(Base, UUIDMixin):
    """Tenant-scoped privacy and disclosure control policy."""

    __tablename__ = "privacy_policies"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    policy_type: Mapped[str] = mapped_column(String(50), default="default", nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    rules: Mapped[dict] = mapped_column(JSON, nullable=False)  # min_contributors, suppress_range_min/max, etc.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )


class DisclosureDecision(Base, UUIDMixin):
    """Audit log of formal disclosure control determinations."""

    __tablename__ = "disclosure_decisions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    request_type: Mapped[str] = mapped_column(String(100), nullable=False)
    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    geography_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("geographies.id", ondelete="SET NULL"),
        nullable=True,
    )
    metric_codes: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    time_range_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    time_range_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decision: Mapped[DisclosureDecisionStatus] = mapped_column(
        pg_enum(DisclosureDecisionStatus, "disclosure_decision_status_enum"),
        nullable=False,
    )
    conditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )


class ExportJob(Base, UUIDMixin):
    """Restricted aggregate data export job with disclosure review."""

    __tablename__ = "export_jobs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    export_type: Mapped[str] = mapped_column(String(50), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[ExportJobStatus] = mapped_column(
        pg_enum(ExportJobStatus, "export_job_status_enum"),
        default=ExportJobStatus.PENDING,
        nullable=False,
        index=True,
    )
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    privacy_policy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    disclosure_reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )


class AuditEvent(Base, UUIDMixin):
    """Immutable append-only audit event log."""

    __tablename__ = "audit_events"

    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        Index("ix_audit_events_tenant_created", "tenant_id", "created_at"),
        Index("ix_audit_events_resource", "resource_type", "resource_id"),
    )

