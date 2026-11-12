"""Alert and evidence models."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin, pg_enum

__all__ = [
    "Hazard",
    "EvidenceClass",
    "AlertSeverity",
    "AlertStatus",
    "Alert",
    "AlertEvidence",
    "AlertStateEvent",
    "AlertRelationship",
]


class Hazard(str, enum.Enum):
    HEAT_ILLNESS = "heat_illness"
    RESPIRATORY_AIR_QUALITY = "respiratory_air_quality"
    INFECTIOUS_DISEASE = "infectious_disease"
    WORKPLACE_SAFETY = "workplace_safety"
    DATA_QUALITY = "data_quality"


class EvidenceClass(str, enum.Enum):
    ENVIRONMENTAL_WATCH = "environmental_watch"
    CORROBORATED_HEALTH_WARNING = "corroborated_health_warning"
    UNCORROBORATED_HEALTH_ANOMALY = "uncorroborated_health_anomaly"
    SAFETY_ESCALATION = "safety_escalation"
    INSUFFICIENT_DATA = "insufficient_data"
    DATA_QUALITY_ISSUE = "data_quality_issue"


class AlertSeverity(str, enum.Enum):
    ADVISORY = "advisory"
    WATCH = "watch"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertStatus(str, enum.Enum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    ACTION_PLANNED = "action_planned"
    MONITORING = "monitoring"
    RESOLVED = "resolved"
    DISMISSED_DATA_ISSUE = "dismissed_data_issue"
    DISMISSED_NOT_ACTIONABLE = "dismissed_not_actionable"
    REOPENED = "reopened"


class Alert(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alert_tenant_hazard_status", "tenant_id", "hazard", "status"),
        Index("ix_alert_tenant_episode", "tenant_id", "episode_key"),
        Index("ix_alert_tenant_geography", "tenant_id", "geography_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    hazard: Mapped[Hazard] = mapped_column(
        pg_enum(Hazard, "hazard", create_constraint=True), nullable=False
    )
    evidence_class: Mapped[EvidenceClass] = mapped_column(
        pg_enum(EvidenceClass, "evidence_class", create_constraint=True), nullable=False
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        pg_enum(AlertSeverity, "alert_severity", create_constraint=True), nullable=False
    )
    status: Mapped[AlertStatus] = mapped_column(
        pg_enum(AlertStatus, "alert_status", create_constraint=True), nullable=False, default=AlertStatus.NEW
    )
    geography_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("geographies.id"), nullable=False
    )
    workplace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workplaces.id"), nullable=True
    )
    target_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    target_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    first_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    latest_revision_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    episode_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    episode_window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    episode_window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    responsible_role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    evidence_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    evidence_score_components: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    suppression_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    suppression_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    suppression_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suppressed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    detection_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_runs.id"), nullable=True
    )
    baseline_model_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("baseline_models.id"), nullable=True
    )
    playbook_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("playbooks.id"), nullable=True
    )
    privacy_policy_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    evidences: Mapped[list[AlertEvidence]] = relationship("AlertEvidence", back_populates="alert", lazy="selectin")
    state_events: Mapped[list[AlertStateEvent]] = relationship("AlertStateEvent", back_populates="alert")
    geography = relationship("Geography", foreign_keys=[geography_id])
    workplace = relationship("Workplace", foreign_keys=[workplace_id])
    relationships_from: Mapped[list[AlertRelationship]] = relationship(
        "AlertRelationship", back_populates="alert", foreign_keys="AlertRelationship.alert_id"
    )


class AlertEvidence(Base, UUIDMixin):
    __tablename__ = "alert_evidences"

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False
    )
    signal_family: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=True
    )
    metric_code: Mapped[str] = mapped_column(String(100), nullable=False)
    observed_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    expected_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    excess: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    rate_difference: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    standardised_residual: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    prediction_interval_lower: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    prediction_interval_upper: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    ewma_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    ewma_threshold: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    baseline_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    baseline_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    native_temporal_resolution: Mapped[str | None] = mapped_column(String(50), nullable=True)
    native_spatial_resolution: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_freshness_minutes: Mapped[int | None] = mapped_column(nullable=True)
    completeness: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    location_uncertainty: Mapped[str | None] = mapped_column(String(50), nullable=True)
    denominator_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    denominator_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    data_label: Mapped[str | None] = mapped_column(String(20), nullable=True)
    model_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    threshold_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    alert: Mapped[Alert] = relationship("Alert", back_populates="evidences")


class AlertStateEvent(Base, UUIDMixin):
    __tablename__ = "alert_state_events"

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    alert: Mapped[Alert] = relationship("Alert", back_populates="state_events")


class AlertRelationship(Base, UUIDMixin):
    __tablename__ = "alert_relationships"

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False
    )
    related_alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False)  # supersedes, related, escalation
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    alert: Mapped[Alert] = relationship("Alert", foreign_keys=[alert_id], back_populates="relationships_from")
    related_alert: Mapped[Alert] = relationship("Alert", foreign_keys=[related_alert_id])
