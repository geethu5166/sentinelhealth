"""Overview and dashboard schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel


class SeverityCount(BaseModel):
    severity: str
    count: int


class ActiveEpisode(BaseModel):
    id: uuid.UUID
    hazard: str
    severity: str
    evidence_class: str
    status: str
    geography_name: str
    target_period_start: datetime
    target_period_end: datetime
    first_detected_at: datetime
    contributing_signal_count: int


class SourceHealth(BaseModel):
    id: uuid.UUID
    name: str
    signal_family: str
    status: str  # fresh, stale, critical
    freshness_minutes: int
    threshold_minutes: int
    last_received_at: Optional[datetime] = None


class OverviewResponse(BaseModel):
    active_alert_count: int
    severity_breakdown: List[SeverityCount]
    pending_task_count: int
    sources_online_count: int
    total_sources_count: int
    last_update_at: Optional[datetime] = None
    active_episodes: List[ActiveEpisode]
    sources: List[SourceHealth]
    data_mode: str = "awaiting_feeds"

