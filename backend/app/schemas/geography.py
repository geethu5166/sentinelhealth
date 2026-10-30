"""Geography and Workplace schemas."""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict


class GeographyRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    code: str
    name: str
    level: str
    parent_id: Optional[uuid.UUID] = None
    population_estimate: Optional[int] = None
    population_year: Optional[int] = None
    properties: Optional[Dict[str, Any]] = None
    version: int
    is_active: bool
    geojson: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class WorkplaceRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    code: str
    name: str
    site_type: str
    address_text: Optional[str] = None
    geography_id: Optional[uuid.UUID] = None
    worker_count_estimate: Optional[int] = None
    is_active: bool
    properties: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

