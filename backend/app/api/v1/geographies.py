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
            site_type=w.site_type.value,
            address_text=w.address_text,
            geography_id=w.geography_id,
            worker_count_estimate=w.worker_count_estimate,
            is_active=w.is_active,
            properties=w.properties,
        )
        for w in workplaces
    ]


@router.get("/map-layer")
@router.get("/geographies/map-layer")
async def get_privacy_safe_map_layer(
    metric_code: str,
    period: str = "24h",
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns privacy-safe GeoJSON FeatureCollection for MapLibre visualization.
    Enforces server-side disclosure control:
    - Never exposes small-cell counts (1-4) or low contributor cells (<10) in GeoJSON properties.
    - Explicitly categorizes map status: 'elevated', 'valid_non_elevated', 'suppressed', 'insufficient_data', 'unavailable'.
    - Supports uncertain/missing geolocation without invented coordinates (geometry=None).
    - Calculates incidence rates only when numerator is unsuppressed and denominator is valid.
    """
    from app.models.signal import SignalRecord
    from app.privacy.suppression import default_disclosure_checker

    geo_query = select(Geography).where(
        Geography.tenant_id == current_user.current_tenant_id,
        Geography.is_active == True,  # noqa: E712
    )
    geo_res = await db.execute(geo_query)
    geos = geo_res.scalars().all()

    # Query latest signals for each geography
    sig_query = select(SignalRecord).where(
        SignalRecord.tenant_id == current_user.current_tenant_id,
        SignalRecord.metric_code == metric_code,
        SignalRecord.is_current == True,  # noqa: E712
    )
    sig_res = await db.execute(sig_query)
    signals = sig_res.scalars().all()
    sig_by_geo = {s.geography_id: s for s in signals if s.geography_id}

    features = []
    for g in geos:
        sig = sig_by_geo.get(g.id)

        # Geolocation handling: do not invent coordinates if geometry is absent
        geom = g.properties.get("geojson") if g.properties else None

        if sig is None:
            status = "unavailable"
            is_suppressed = False
            suppression_reason = None
            display_val = None
            rate_per_100k = None
        else:
            is_sensitive = sig.signal_family.value in ["clinical_service", "workforce"]
            suppress, reason = default_disclosure_checker.should_suppress_cell(
                value=sig.value,
                contributor_count=sig.contributor_count,
                is_sensitive_health_event=is_sensitive,
            )

            if suppress:
                status = "suppressed"
                is_suppressed = True
                suppression_reason = reason or "Suppressed: this group does not meet the minimum reporting threshold."
                display_val = None
                rate_per_100k = None  # Never compute rate on suppressed numerator
            elif sig.value is None or (sig.properties and sig.properties.get("insufficient_data")):
                status = "insufficient_data"
                is_suppressed = False
                suppression_reason = None
                display_val = None
                rate_per_100k = None
            else:
                is_suppressed = False
                suppression_reason = None
                display_val = float(sig.value) if sig.value is not None else None

                # Status determination
                is_elevated = (
                    (metric_code == "pm25_concentration" and display_val is not None and display_val >= 60.0)
                    or (metric_code == "apparent_temperature" and display_val is not None and display_val >= 39.0)
                    or (sig.excess is not None and float(sig.excess) > 0)
                )
                status = "elevated" if is_elevated else "valid_non_elevated"

                # Compatible encounter rate: requires unsuppressed count and valid population denominator
                if display_val is not None and g.population_estimate and g.population_estimate > 0:
                    rate_per_100k = round((display_val / g.population_estimate) * 100_000, 2)
                else:
                    rate_per_100k = None

        features.append({
            "type": "Feature",
            "geometry": geom,  # null if not geometrically defined; no invented points
            "properties": {
                "geography_id": str(g.id),
                "geography_code": g.code,
                "geography_name": g.name,
                "status": status,
                "metric_code": metric_code,
                "value": display_val,
                "unit": sig.unit if sig else None,
                "is_suppressed": is_suppressed,
                "suppression_reason": suppression_reason,
                "encounter_rate_per_100k": rate_per_100k,
                "rate_label": "Respiratory encounters per 100,000 catchment population during the selected period (not disease incidence)",
                "location_confidence": sig.location_confidence.value if sig else "unknown",
                "location_basis": sig.location_basis.value if sig else "unspecified",
            },
        })

    return {
        "type": "FeatureCollection",
        "metric_code": metric_code,
        "features": features,
    }

