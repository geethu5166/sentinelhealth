"""Preventive task schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class TaskSummary(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    alert_id: uuid.UUID
    title: str
    assigned_role: str
    assigned_to_user_id: Optional[uuid.UUID] = None
    status: str
    priority: int
    due_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    approval_required: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskDetail(TaskSummary):
    description: Optional[str] = None
    recommendation_id: Optional[uuid.UUID] = None
    completion_evidence: Optional[str] = None
    completion_notes: Optional[str] = None
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    alert_hazard: Optional[str] = None
    alert_severity: Optional[str] = None


class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=500)
    description: Optional[str] = None
    assigned_role: str = Field(..., min_length=2, max_length=100)
    assigned_to_user_id: Optional[uuid.UUID] = None
    priority: int = Field(default=1, ge=0, le=4)
    due_at: Optional[datetime] = None
    approval_required: bool = False
    recommendation_id: Optional[uuid.UUID] = None


class TaskUpdateRequest(BaseModel):
    status: Optional[str] = None
    assigned_to_user_id: Optional[uuid.UUID] = None
    completion_evidence: Optional[str] = None
    completion_notes: Optional[str] = None
    approval_decision: Optional[str] = None  # approved, rejected

