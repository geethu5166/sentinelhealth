"""Geographies and Workplaces API routes."""

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.geography import Geography, Workplace
from app.schemas.auth import UserInfo
from app.schemas.geography import GeographyRead, WorkplaceRead

router = APIRouter(tags=["geography"])


@router.get("/geographies", response_model=List[GeographyRead])
async def list_geographies(
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns approved aggregate districts and zones for the authenticated tenant."""
    query = select(Geography).where(
        Geography.tenant_id == current_user.current_tenant_id,
        Geography.is_active == True,  # noqa: E712
    )
    result = await db.execute(query)
    geos = result.scalars().all()
    return [
        GeographyRead(
            id=g.id,
            tenant_id=g.tenant_id,
            code=g.code,
            name=g.name,
            level=g.level.value,
            parent_id=g.parent_id,
            population_estimate=g.population_estimate,
            population_year=g.population_year,
            properties=g.properties,
            version=g.version,
            is_active=g.is_active,
        )
        for g in geos
    ]


@router.get("/workplaces", response_model=List[WorkplaceRead])
async def list_workplaces(
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns authorized workplaces mapped to aggregate geographies."""
    query = select(Workplace).where(
        Workplace.tenant_id == current_user.current_tenant_id,
        Workplace.is_active == True,  # noqa: E712
    )
    result = await db.execute(query)
    workplaces = result.scalars().all()
    return [
        WorkplaceRead(
            id=w.id,
            tenant_id=w.tenant_id,
            code=w.code,
            name=w.name,
            site_type=w.site_type,
            address_text=w.address_text,
            geography_id=w.geography_id,
            worker_count_estimate=w.worker_count_estimate,
            is_active=w.is_active,
            properties=w.properties,
        )
        for w in workplaces
    ]

