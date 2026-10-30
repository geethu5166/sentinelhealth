"""Base connector interface for environmental and health signal ingestion."""

from __future__ import annotations

import abc
from datetime import datetime
from typing import Any, Dict, List
from pydantic import BaseModel


class NormalizedRecord(BaseModel):
    source_record_id: str
    metric_code: str
    signal_family: str
    value: float
    unit: str
    numerator: float | None = None
    denominator: float | None = None
    denominator_unit: str | None = None
    contributor_count: int | None = None
    contributor_definition: str | None = None
    period_start: datetime
    period_end: datetime
    observed_at: datetime
    source_available_at: datetime
    geography_id: str | None = None
    workplace_id: str | None = None
    location_basis: str = "unknown"
    location_confidence: str = "unknown"
    data_label: str = "observed"
    quality_flags: Dict[str, Any] = {}
    completeness: float | None = 1.0
    provenance: str = "connector"


class BaseConnector(abc.ABC):
    """Abstract base connector defining contract for all data sources."""

    def __init__(self, source_code: str, configuration: Dict[str, Any]):
        self.source_code = source_code
        self.configuration = configuration

    @abc.abstractmethod
    async def fetch(self, start_time: datetime, end_time: datetime) -> List[NormalizedRecord]:
        """Fetches and normalizes records for the requested time range."""
        pass

    @abc.abstractmethod
    async def test_connection(self) -> bool:
        """Verifies connector connectivity and credentials."""
        pass

