"""Replay, simulation, reference event, and evaluation result models."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

__all__ = [
    "ReplayStatus",
    "ReplayRun",
    "ReplayScenario",
    "ReferenceEvent",
    "EvaluationResult",
]


class ReplayStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ReplayScenario(Base, UUIDMixin):
    """Deterministic synthetic scenario configuration."""

    __tablename__ = "replay_scenarios"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    hazard: Mapped[str] = mapped_column(String(50), nullable=False)
    configuration: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    reference_events: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    data_label: Mapped[str] = mapped_column(String(50), default="synthetic", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    runs: Mapped[list["ReplayRun"]] = relationship("ReplayRun", back_populates="scenario")
    events: Mapped[list["ReferenceEvent"]] = relationship("ReferenceEvent", back_populates="scenario")


class ReferenceEvent(Base, UUIDMixin):
    """Reference ground truth event for an evaluation scenario (isolated from detection)."""

    __tablename__ = "reference_events"

    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("replay_scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hazard: Mapped[str] = mapped_column(String(50), nullable=False)
    geography_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("geographies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    onset_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence_basis: Mapped[str] = mapped_column(Text, nullable=False)
    earliest_useful_action_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    scenario: Mapped[ReplayScenario] = relationship("ReplayScenario", back_populates="events")


class ReplayRun(Base, UUIDMixin):
    """Execution instance of a replay scenario."""

    __tablename__ = "replay_runs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("replay_scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[ReplayStatus] = mapped_column(
        Enum(ReplayStatus, name="replay_status_enum"),
        default=ReplayStatus.PENDING,
        nullable=False,
        index=True,
    )
    configuration: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    results_summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    scenario: Mapped[ReplayScenario] = relationship("ReplayScenario", back_populates="runs")
    evaluation_results: Mapped[list["EvaluationResult"]] = relationship(
        "EvaluationResult",
        back_populates="run",
        cascade="all, delete-orphan",
    )


class EvaluationResult(Base, UUIDMixin):
    """Standardized surveillance evaluation metric calculation."""

    __tablename__ = "evaluation_results"

    replay_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("replay_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    numerator: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    denominator: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    eligible_observation_time: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    uncertainty_lower: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    uncertainty_upper: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    is_estimable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    run: Mapped[ReplayRun] = relationship("ReplayRun", back_populates="evaluation_results")

