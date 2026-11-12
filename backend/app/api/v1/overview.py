"""Overview and operational summary endpoints."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.alert import Alert, AlertSeverity, AlertStatus
from app.models.playbook import PreventiveTask, TaskStatus
from app.models.signal import DataSource
from app.schemas.auth import UserInfo
from app.schemas.overview import (
    ActiveEpisode,
    OverviewResponse,
    SeverityCount,
    SourceHealth,
)

router = APIRouter(prefix="/overview", tags=["overview"])


@router.get("", response_model=OverviewResponse)
async def get_overview(
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_user.current_tenant_id

    # Active alerts count
    alert_query = select(Alert).options(selectinload(Alert.geography), selectinload(Alert.evidences)).where(
        Alert.tenant_id == tenant_id,
        Alert.status.in_([
            AlertStatus.NEW,
            AlertStatus.ACKNOWLEDGED,
            AlertStatus.INVESTIGATING,
            AlertStatus.ACTION_PLANNED,
            AlertStatus.MONITORING,
        ]),
    )
    alert_res = await db.execute(alert_query)
    alerts = alert_res.scalars().all()

    # Severity breakdown
    sev_counts = {}
    for a in alerts:
        sev_counts[a.severity.value] = sev_counts.get(a.severity.value, 0) + 1

    severity_breakdown = [
        SeverityCount(severity=sev.value, count=sev_counts.get(sev.value, 0))
        for sev in AlertSeverity
    ]

    # Active episodes
    active_episodes = [
        ActiveEpisode(
            id=a.id,
            hazard=a.hazard.value,
            severity=a.severity.value,
            evidence_class=a.evidence_class.value,
            status=a.status.value,
            geography_name=a.geography.name if a.geography else "Unknown District",
            target_period_start=a.target_period_start,
            target_period_end=a.target_period_end,
            first_detected_at=a.first_detected_at,
            contributing_signal_count=len(a.evidences),
        )
        for a in alerts
    ]

    # Pending tasks
    task_res = await db.execute(
        select(func.count(PreventiveTask.id)).where(
            PreventiveTask.tenant_id == tenant_id,
            PreventiveTask.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
        )
    )
    pending_tasks = task_res.scalar_one() or 0

    # Data sources status
    src_res = await db.execute(select(DataSource).where(DataSource.tenant_id == tenant_id))
    sources = src_res.scalars().all()

    source_health_list = []
    for s in sources:
        source_health_list.append(
            SourceHealth(
                id=s.id,
                name=s.name,
                signal_family=s.signal_family.value,
                status="fresh",
                freshness_minutes=15,
                threshold_minutes=s.freshness_threshold_minutes,
                last_received_at=s.updated_at,
            )
        )

    return OverviewResponse(
        active_alert_count=len(alerts),
        severity_breakdown=severity_breakdown,
        pending_task_count=pending_tasks,
        sources_online_count=len([s for s in sources if s.is_active]),
        total_sources_count=len(sources),
        last_update_at=datetime.now(timezone.utc),
        active_episodes=active_episodes,
        sources=source_health_list,
        data_mode="realtime_screening",
    )

