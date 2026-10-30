"""Analytics models: FeatureWindow, BaselineModel, ModelVersion, DetectionRun."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin

__all__ = [
    "AggregationMethod",
    "BaselineModelType",
    "DetectionRunType",
    "DetectionRunStatus",
    "FeatureWindow",
    "BaselineModel",
    "ModelVersion",
    "DetectionRun",
]


class AggregationMethod(str, enum.Enum):
    SUM = "sum"
    MEAN = "mean"
    MEDIAN = "median"
    MAX = "max"
    MIN = "min"
    COUNT = "count"
    RATE = "rate"


class BaselineModelType(str, enum.Enum):
    RECENT_HISTORY = "recent_history"
    POISSON = "poisson"
    NEGATIVE_BINOMIAL = "negative_binomial"
    BINOMIAL = "binomial"


class DetectionRunType(str, enum.Enum):
    SCHEDULED = "scheduled"
    REPLAY = "replay"
    MANUAL = "manual"


class DetectionRunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class FeatureWindow(Base, UUIDMixin):
    __tablename__ = "feature_windows"
    __table_args__ = (
        Index("ix_feature_tenant_metric_geo_window", "tenant_id", "metric_code", "geography_id", "window_start"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    metric_code: Mapped[str] = mapped_column(String(100), nullable=False)
    geography_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("geographies.id"), nullable=False
    )
    workplace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workplaces.id"), nullable=True
    )
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    aggregation_method: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    denominator: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    rate: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    sample_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    contributor_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data_label: Mapped[str] = mapped_column(String(20), nullable=False)
    quality_flags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )


class BaselineModel(Base, UUIDMixin):
    __tablename__ = "baseline_models"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    metric_code: Mapped[str] = mapped_column(String(100), nullable=False)
    geography_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("geographies.id"), nullable=True
    )
    model_type: Mapped[BaselineModelType] = mapped_column(
        Enum(BaselineModelType, name="baseline_model_type", create_constraint=True), nullable=False
    )
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    configuration: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    fitting_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fitting_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    input_snapshot_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    diagnostics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    versions: Mapped[list[ModelVersion]] = relationship("ModelVersion", back_populates="baseline_model")


class ModelVersion(Base, UUIDMixin):
    __tablename__ = "model_versions"

    baseline_model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("baseline_models.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    parameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    diagnostics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    fitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fitted_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    baseline_model: Mapped[BaselineModel] = relationship("BaselineModel", back_populates="versions")


class DetectionRun(Base, UUIDMixin):
    __tablename__ = "detection_runs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    run_type: Mapped[DetectionRunType] = mapped_column(
        Enum(DetectionRunType, name="detection_run_type", create_constraint=True), nullable=False
    )
    status: Mapped[DetectionRunStatus] = mapped_column(
        Enum(DetectionRunStatus, name="detection_run_status", create_constraint=True), nullable=False
    )
    scoring_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    inputs_available_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    configuration_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    results_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
