"""Signals time series and privacy-safe aggregate data routes."""

import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.signal import SignalRecord
from app.privacy.suppression import default_disclosure_checker
from app.schemas.auth import UserInfo
from app.schemas.signal import SignalRecordRead, SignalSeriesPoint, SignalSeriesResponse

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("", response_model=List[SignalRecordRead])
async def list_signals(
    metric_code: Optional[str] = None,
    signal_family: Optional[str] = None,
    geography_id: Optional[uuid.UUID] = None,
    limit: int = Query(default=50, le=100),
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists current aggregate signals with privacy suppression applied."""
    query = select(SignalRecord).where(
        SignalRecord.tenant_id == current_user.current_tenant_id,
        SignalRecord.is_current == True,  # noqa: E712
    )
    if metric_code:
        query = query.where(SignalRecord.metric_code == metric_code)
    if signal_family:
        query = query.where(SignalRecord.signal_family == signal_family)
    if geography_id:
        query = query.where(SignalRecord.geography_id == geography_id)

    query = query.order_by(SignalRecord.period_start.desc()).limit(limit)
    result = await db.execute(query)
    records = result.scalars().all()

    response_items = []
    for r in records:
        is_sensitive = r.signal_family.value in ["clinical_service", "workforce"]
        suppress, reason = default_disclosure_checker.should_suppress_cell(
            value=r.value,
            contributor_count=r.contributor_count,
            is_sensitive_health_event=is_sensitive,
        )

        response_items.append(
            SignalRecordRead(
                id=r.id,
                tenant_id=r.tenant_id,
                source_id=r.source_id,
                metric_code=r.metric_code,
                signal_family=r.signal_family.value,
                value=None if suppress else r.value,
                unit=r.unit,
                numerator=None if suppress else r.numerator,
                denominator=None if suppress else r.denominator,
                denominator_unit=r.denominator_unit,
                contributor_count=None if suppress else r.contributor_count,
                period_start=r.period_start,
                period_end=r.period_end,
                observed_at=r.observed_at,
                source_available_at=r.source_available_at,
                geography_id=r.geography_id,
                workplace_id=r.workplace_id,
                location_basis=r.location_basis.value,
                location_confidence=r.location_confidence.value,
                data_label=r.data_label.value,
                is_suppressed=suppress,
                suppression_reason=reason,
            )
        )

    return response_items


@router.get("/{metric_code}/series", response_model=SignalSeriesResponse)
async def get_signal_series(
    metric_code: str,
    geography_id: Optional[uuid.UUID] = None,
    limit: int = Query(default=60, le=365),
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns chronologically ordered series points for observed/expected charting."""
    query = select(SignalRecord).where(
        SignalRecord.tenant_id == current_user.current_tenant_id,
        SignalRecord.metric_code == metric_code,
    )
    if geography_id:
        query = query.where(SignalRecord.geography_id == geography_id)

    query = query.order_by(SignalRecord.period_start.asc()).limit(limit)
    result = await db.execute(query)
    records = result.scalars().all()

    points = []
    unit = "unknown"
    data_label = "synthetic"

    for r in records:
        unit = r.unit
        data_label = r.data_label.value
        is_sensitive = r.signal_family.value in ["clinical_service", "workforce"]
        suppress, _ = default_disclosure_checker.should_suppress_cell(
            value=r.value,
            contributor_count=r.contributor_count,
            is_sensitive_health_event=is_sensitive,
        )

        points.append(
            SignalSeriesPoint(
                timestamp=r.period_start,
                value=None if suppress else r.value,
                expected=None,
                lower_bound=None,
                upper_bound=None,
                is_suppressed=suppress,
                is_anomaly=False,
            )
        )

    return SignalSeriesResponse(
        metric_code=metric_code,
        unit=unit,
        geography_id=geography_id,
        data_label=data_label,
        points=points,
    )

