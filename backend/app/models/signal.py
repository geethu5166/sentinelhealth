"""Signal ingestion and record models."""

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
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

__all__ = [
    "SignalFamily",
    "SourceType",
    "IngestionStatus",
    "LocationBasis",
    "LocationConfidence",
    "DataLabel",
    "DataSource",
    "IngestionRun",
    "IngestionError",
    "SignalRecord",
    "SignalRecordVersion",
]


class SignalFamily(str, enum.Enum):
    ENVIRONMENTAL = "environmental"
    CLINICAL_SERVICE = "clinical_service"
    WORKFORCE = "workforce"
    WORKPLACE_SAFETY = "workplace_safety"
    LABORATORY = "laboratory"


class SourceType(str, enum.Enum):
    CONNECTOR = "connector"
    FILE_UPLOAD = "file_upload"
    API = "api"


class IngestionStatus(str, enum.Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    ACCEPTED = "accepted"
    PARTIAL = "partial"
    REJECTED = "rejected"
    FAILED = "failed"


class LocationBasis(str, enum.Enum):
    RESIDENCE = "residence"
    WORKPLACE = "workplace"
    EXPOSURE_SITE = "exposure_site"
    FACILITY = "facility"
    CATCHMENT = "catchment"
    MODEL_GRID = "model_grid"
    UNKNOWN = "unknown"


class LocationConfidence(str, enum.Enum):
    EXACT = "exact"
    MAPPED = "mapped"
    ESTIMATED = "estimated"
    UNKNOWN = "unknown"


class DataLabel(str, enum.Enum):
    REAL = "real"
    SYNTHETIC = "synthetic"
    MODELLED = "modelled"
    OBSERVED = "observed"


class DataSource(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "data_sources"
    __table_args__ = (
        Index("ix_data_source_tenant_code", "tenant_id", "code"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    signal_family: Mapped[SignalFamily] = mapped_column(
        Enum(SignalFamily, name="signal_family", create_constraint=True), nullable=False
    )
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="source_type", create_constraint=True), nullable=False
    )
    provider: Mapped[str | None] = mapped_column(String(255), nullable=True)
    schema_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    expected_cadence_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    freshness_threshold_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    configuration: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    ingestion_runs: Mapped[list[IngestionRun]] = relationship("IngestionRun", back_populates="source")
    signal_records: Mapped[list[SignalRecord]] = relationship("SignalRecord", back_populates="source")


class IngestionRun(Base, UUIDMixin):
    __tablename__ = "ingestion_runs"
    __table_args__ = (
        Index("ix_ingestion_run_tenant_source", "tenant_id", "source_id"),
        Index("ix_ingestion_run_idempotency", "idempotency_key", unique=True),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[IngestionStatus] = mapped_column(
        Enum(IngestionStatus, name="ingestion_status", create_constraint=True), nullable=False
    )
    records_received: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_accepted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_rejected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_quarantined: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    source: Mapped[DataSource] = relationship("DataSource", back_populates="ingestion_runs")
    errors: Mapped[list[IngestionError]] = relationship("IngestionError", back_populates="run")


class IngestionError(Base, UUIDMixin):
    __tablename__ = "ingestion_errors"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingestion_runs.id", ondelete="CASCADE"), nullable=False
    )
    record_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    field_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_type: Mapped[str] = mapped_column(String(100), nullable=False)
    error_message: Mapped[str] = mapped_column(String(2000), nullable=False)
    raw_value: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    run: Mapped[IngestionRun] = relationship("IngestionRun", back_populates="errors")


class SignalRecord(Base, UUIDMixin):
    __tablename__ = "signal_records"
    __table_args__ = (
        UniqueConstraint("tenant_id", "source_id", "metric_code", "period_start", "geography_id", "workplace_id", "record_version", name="uq_signal_records_idempotency"),
        Index("ix_signal_tenant_source_metric_period", "tenant_id", "source_id", "metric_code", "period_start"),
        Index("ix_signal_tenant_geography", "tenant_id", "geography_id"),
        Index("ix_signal_tenant_workplace", "tenant_id", "workplace_id"),
        Index("ix_signal_tenant_metric_current", "tenant_id", "metric_code", "is_current"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False
    )
    source_record_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    record_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    schema_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    signal_family: Mapped[str] = mapped_column(String(50), nullable=False)
    metric_code: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    numerator: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    denominator: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    denominator_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    contributor_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    contributor_definition: Mapped[str | None] = mapped_column(String(255), nullable=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_available_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    revised_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    forecast_issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lead_horizon_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    forecast_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    forecast_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    native_temporal_resolution: Mapped[str | None] = mapped_column(String(50), nullable=True)
    native_spatial_resolution: Mapped[str | None] = mapped_column(String(50), nullable=True)
    geography_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("geographies.id"), nullable=True
    )
    workplace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workplaces.id"), nullable=True
    )
    location_basis: Mapped[LocationBasis | None] = mapped_column(
        Enum(LocationBasis, name="location_basis", create_constraint=True), nullable=True
    )
    location_confidence: Mapped[LocationConfidence | None] = mapped_column(
        Enum(LocationConfidence, name="location_confidence", create_constraint=True), nullable=True
    )
    mapping_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    quality_flags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    completeness: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    provenance: Mapped[str | None] = mapped_column(String(500), nullable=True)
    data_label: Mapped[DataLabel] = mapped_column(
        Enum(DataLabel, name="data_label", create_constraint=True), nullable=False
    )
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    source: Mapped[DataSource] = relationship("DataSource", back_populates="signal_records")
    versions: Mapped[list[SignalRecordVersion]] = relationship("SignalRecordVersion", back_populates="signal_record")


class SignalRecordVersion(Base, UUIDMixin):
    __tablename__ = "signal_record_versions"

    signal_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("signal_records.id", ondelete="CASCADE"), nullable=False
    )
    record_version: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    numerator: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    denominator: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    quality_flags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    change_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    signal_record: Mapped[SignalRecord] = relationship("SignalRecord", back_populates="versions")
