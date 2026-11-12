"""Alert and evidence schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AlertEvidenceRead(BaseModel):
    id: uuid.UUID
    signal_family: str
    source_id: Optional[uuid.UUID] = None
    metric_code: str
    observed_value: Optional[Decimal] = None
    expected_value: Optional[Decimal] = None
    excess: Optional[Decimal] = None
    rate_difference: Optional[Decimal] = None
    standardised_residual: Optional[Decimal] = None
    prediction_interval_lower: Optional[Decimal] = None
    prediction_interval_upper: Optional[Decimal] = None
    ewma_value: Optional[Decimal] = None
    ewma_threshold: Optional[Decimal] = None
    baseline_period_start: Optional[datetime] = None
    baseline_period_end: Optional[datetime] = None
    native_temporal_resolution: Optional[str] = None
    native_spatial_resolution: Optional[str] = None
    source_freshness_minutes: Optional[int] = None
    completeness: Optional[Decimal] = None
    location_uncertainty: Optional[str] = None
    denominator_value: Optional[Decimal] = None
    denominator_unit: Optional[str] = None
    data_label: Optional[str] = None
    model_type: Optional[str] = None
    model_version: Optional[str] = None
    threshold_version: Optional[str] = None
    is_suppressed: bool = False

    model_config = ConfigDict(from_attributes=True)


class AlertStateEventRead(BaseModel):
    id: uuid.UUID
    from_status: Optional[str] = None
    to_status: str
    actor_id: Optional[uuid.UUID] = None
    reason: Optional[str] = None
    event_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertSummary(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    hazard: str
    evidence_class: str
    severity: str
    status: str
    geography_id: uuid.UUID
    geography_name: Optional[str] = None
    workplace_id: Optional[uuid.UUID] = None
    workplace_name: Optional[str] = None
    target_period_start: datetime
    target_period_end: datetime
    first_detected_at: datetime
    latest_revision_at: Optional[datetime] = None
    episode_key: Optional[str] = None
    responsible_role: Optional[str] = None
    evidence_score: Optional[Decimal] = None
    suppression_status: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertDetail(AlertSummary):
    evidence_score_components: Optional[Dict[str, Any]] = None
    suppression_reason: Optional[str] = None
    playbook_id: Optional[uuid.UUID] = None
    privacy_policy_version: Optional[str] = None
    evidences: List[AlertEvidenceRead] = Field(default_factory=list)
    state_events: List[AlertStateEventRead] = Field(default_factory=list)
    recommended_action: Optional[str] = None
    recommendation_assumptions: Optional[Dict[str, Any]] = None


class AlertTransitionRequest(BaseModel):
    to_status: str = Field(..., description="Target status: acknowledged, investigating, action_planned, monitoring, resolved, dismissed_data_issue, dismissed_not_actionable, reopened")
    reason: str = Field(..., min_length=3, description="Mandatory reason for audit trail")
    metadata: Optional[Dict[str, Any]] = None

