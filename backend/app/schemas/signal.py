"""Data source and signal schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DataSourceBase(BaseModel):
    code: str
    name: str
    signal_family: str
    source_type: str
    provider: str
    schema_version: str
    expected_cadence_minutes: int
    freshness_threshold_minutes: int
    configuration: Optional[Dict[str, Any]] = None


class DataSourceCreate(DataSourceBase):
    pass


class DataSourceRead(DataSourceBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_ingestion_at: Optional[datetime] = None
    freshness_status: Optional[str] = "unknown"  # fresh, stale, critical, unknown

    model_config = ConfigDict(from_attributes=True)


class IngestionRunRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    source_id: uuid.UUID
    status: str
    records_received: int
    records_accepted: int
    records_rejected: int
    records_quarantined: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_summary: Optional[str] = None
    idempotency_key: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SignalRecordRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    source_id: uuid.UUID
    metric_code: str
    signal_family: str
    value: Optional[Decimal] = None
    unit: str
    numerator: Optional[Decimal] = None
    denominator: Optional[Decimal] = None
    denominator_unit: Optional[str] = None
    contributor_count: Optional[int] = None
    period_start: datetime
    period_end: datetime
    observed_at: datetime
    source_available_at: datetime
    geography_id: Optional[uuid.UUID] = None
    workplace_id: Optional[uuid.UUID] = None
    location_basis: str
    location_confidence: str
    data_label: str
    is_suppressed: bool = False
    suppression_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SignalSeriesPoint(BaseModel):
    timestamp: datetime
    value: Optional[Decimal] = None
    expected: Optional[Decimal] = None
    lower_bound: Optional[Decimal] = None
    upper_bound: Optional[Decimal] = None
    is_suppressed: bool = False
    is_anomaly: bool = False


class SignalSeriesResponse(BaseModel):
    metric_code: str
    unit: str
    geography_id: Optional[uuid.UUID] = None
    workplace_id: Optional[uuid.UUID] = None
    data_label: str
    points: List[SignalSeriesPoint]

