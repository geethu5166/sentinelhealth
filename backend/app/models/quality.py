"""Data quality snapshot model."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin

__all__ = [
    "QualitySnapshot",
]


class QualitySnapshot(Base, UUIDMixin):
    __tablename__ = "quality_snapshots"
    __table_args__ = (
        Index("ix_quality_tenant_source_date", "tenant_id", "source_id", "snapshot_date"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False
    )
    geography_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("geographies.id"), nullable=True
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    completeness_pct: Mapped[float] = mapped_column(Float, nullable=False)
    freshness_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    records_expected: Mapped[int] = mapped_column(Integer, nullable=False)
    records_received: Mapped[int] = mapped_column(Integer, nullable=False)
    invalid_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quality_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    issues: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
