"""Playbook, Recommendation, PreventiveTask, TaskEvent models."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

__all__ = [
    "PlaybookApprovalStatus",
    "TaskStatus",
    "TaskPriority",
    "ActionTier",
    "Playbook",
    "PlaybookVersion",
    "Recommendation",
    "PreventiveTask",
    "TaskEvent",
]


class ActionTier(str, enum.Enum):
    TIER_1_PREPARATION = "tier_1_preparation"
    TIER_2_ADJUSTED_OPERATIONS = "tier_2_adjusted_operations"
    TIER_3_RESTRICTED_ACTIVITY = "tier_3_restricted_activity"
    TIER_4_EMERGENCY_SUSPENSION = "tier_4_emergency_suspension"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PlaybookApprovalStatus(str, enum.Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    RETIRED = "retired"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    OVERDUE = "overdue"


class Playbook(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "playbooks"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )
    hazard: Mapped[str] = mapped_column(String(100), nullable=False)
    jurisdiction: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    evidence_requirements: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    contraindications: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    action_tiers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    approval_status: Mapped[PlaybookApprovalStatus] = mapped_column(
        Enum(PlaybookApprovalStatus, name="playbook_approval_status", create_constraint=True),
        nullable=False,
        default=PlaybookApprovalStatus.DRAFT,
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_review_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    versions: Mapped[list[PlaybookVersion]] = relationship("PlaybookVersion", back_populates="playbook")
    recommendations: Mapped[list[Recommendation]] = relationship("Recommendation", back_populates="playbook")


class PlaybookVersion(Base, UUIDMixin):
    __tablename__ = "playbook_versions"

    playbook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("playbooks.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    playbook: Mapped[Playbook] = relationship("Playbook", back_populates="versions")


class Recommendation(Base, UUIDMixin):
    __tablename__ = "recommendations"

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False
    )
    playbook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("playbooks.id"), nullable=False
    )
    playbook_version: Mapped[int] = mapped_column(Integer, nullable=False)
    action_tier: Mapped[str] = mapped_column(String(50), nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    accountable_role: Mapped[str] = mapped_column(String(100), nullable=False)
    approval_role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    completion_evidence_required: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_window_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assumptions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    playbook: Mapped[Playbook] = relationship("Playbook", back_populates="recommendations")
    tasks: Mapped[list[PreventiveTask]] = relationship("PreventiveTask", back_populates="recommendation")


class PreventiveTask(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "preventive_tasks"
    __table_args__ = (
        Index("ix_task_tenant_status", "tenant_id", "status"),
        Index("ix_task_tenant_alert", "tenant_id", "alert_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False
    )
    recommendation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recommendations.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_role: Mapped[str] = mapped_column(String(100), nullable=False)
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status", create_constraint=True),
        nullable=False,
        default=TaskStatus.PENDING,
    )
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completion_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    completion_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    approval_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    recommendation: Mapped[Recommendation | None] = relationship("Recommendation", back_populates="tasks")
    alert = relationship("Alert", foreign_keys=[alert_id])
    events: Mapped[list[TaskEvent]] = relationship("TaskEvent", back_populates="task")


class TaskEvent(Base, UUIDMixin):
    __tablename__ = "task_events"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("preventive_tasks.id", ondelete="CASCADE"), nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    task: Mapped[PreventiveTask] = relationship("PreventiveTask", back_populates="events")
