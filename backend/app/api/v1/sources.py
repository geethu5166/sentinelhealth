"""Data sources and source quality API routes."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.quality import QualitySnapshot
from app.models.signal import DataSource, SignalFamily, SignalRecord, SourceType
from app.schemas.auth import UserInfo
from app.schemas.signal import DataSourceCreate, DataSourceRead
from app.services.freshness import classify_freshness

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=List[DataSourceRead])
async def list_sources(
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists configured data sources for the current tenant."""
    query = select(DataSource).where(DataSource.tenant_id == current_user.current_tenant_id)
    result = await db.execute(query)
    sources = result.scalars().all()
    latest_by_source = dict(
        (
            await db.execute(
                select(SignalRecord.source_id, func.max(SignalRecord.ingested_at))
                .where(SignalRecord.tenant_id == current_user.current_tenant_id)
                .group_by(SignalRecord.source_id)
            )
        ).all()
    )
    payload = []
    for s in sources:
        last_seen = latest_by_source.get(s.id) or s.updated_at
        freshness_status, _age = classify_freshness(last_seen, s.freshness_threshold_minutes)
        payload.append(
            DataSourceRead(
                id=s.id,
                tenant_id=s.tenant_id,
                code=s.code,
                name=s.name,
                signal_family=s.signal_family.value,
                source_type=s.source_type.value,
                provider=s.provider,
                schema_version=s.schema_version,
                expected_cadence_minutes=s.expected_cadence_minutes,
                freshness_threshold_minutes=s.freshness_threshold_minutes,
                is_active=s.is_active,
                configuration=s.configuration,
                created_at=s.created_at,
                updated_at=s.updated_at,
                last_ingestion_at=last_seen,
                freshness_status=freshness_status,
            )
        )
    return payload


@router.post("", response_model=DataSourceRead, dependencies=[Depends(require_role(["data_steward", "platform_admin"]))])
async def create_source(
    payload: DataSourceCreate,
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Registers a new data source configuration."""
    source = DataSource(
        tenant_id=current_user.current_tenant_id,
        code=payload.code,
        name=payload.name,
        signal_family=SignalFamily(payload.signal_family),
        source_type=SourceType(payload.source_type),
        provider=payload.provider,
        schema_version=payload.schema_version,
        expected_cadence_minutes=payload.expected_cadence_minutes,
        freshness_threshold_minutes=payload.freshness_threshold_minutes,
        configuration=payload.configuration,
        is_active=True,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return DataSourceRead(
        id=source.id,
        tenant_id=source.tenant_id,
        code=source.code,
        name=source.name,
        signal_family=source.signal_family.value,
        source_type=source.source_type.value,
        provider=source.provider,
        schema_version=source.schema_version,
        expected_cadence_minutes=source.expected_cadence_minutes,
        freshness_threshold_minutes=source.freshness_threshold_minutes,
        is_active=source.is_active,
        configuration=source.configuration,
        created_at=source.created_at,
        updated_at=source.updated_at,
        freshness_status="fresh",
    )


@router.get("/{source_id}/quality")
async def get_source_quality(
    source_id: uuid.UUID,
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves recent quality audit snapshots for a data source."""
    query = (
        select(QualitySnapshot)
        .where(
            QualitySnapshot.tenant_id == current_user.current_tenant_id,
            QualitySnapshot.source_id == source_id,
        )
        .order_by(QualitySnapshot.snapshot_date.desc())
        .limit(30)
    )
    result = await db.execute(query)
    snapshots = result.scalars().all()
    return {"source_id": str(source_id), "snapshots": snapshots}

