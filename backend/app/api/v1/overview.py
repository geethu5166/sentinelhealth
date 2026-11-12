"""Overview and operational summary endpoints."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.alert import Alert, AlertEvidence, AlertSeverity, AlertStatus
from app.models.playbook import PreventiveTask, TaskStatus
from app.models.signal import DataLabel, DataSource, SignalRecord
from app.schemas.auth import UserInfo
from app.schemas.overview import (
    ActiveEpisode,
    OverviewResponse,
    SeverityCount,
    SourceHealth,
)
from app.services.freshness import classify_freshness

router = APIRouter(prefix="/overview", tags=["overview"])


async def _resolve_data_mode(db: AsyncSession, tenant_id) -> str:
    """Derive overview provenance from actual stored signal/evidence labels."""
    signal_labels = (
        await db.execute(
            select(SignalRecord.data_label)
            .where(SignalRecord.tenant_id == tenant_id)
            .distinct()
        )
    ).scalars().all()

    evidence_labels = (
        await db.execute(
            select(AlertEvidence.data_label)
            .join(Alert, AlertEvidence.alert_id == Alert.id)
            .where(Alert.tenant_id == tenant_id, AlertEvidence.data_label.is_not(None))
            .distinct()
        )
    ).scalars().all()

    labels: set[str] = set()
    for label in signal_labels:
        labels.add(label.value if hasattr(label, "value") else str(label))
    for label in evidence_labels:
        labels.add(str(label))

    if not labels:
        return "awaiting_feeds"
    if labels == {DataLabel.SYNTHETIC.value} or labels == {"synthetic"}:
        return "synthetic_demonstration"
    if DataLabel.SYNTHETIC.value in labels or "synthetic" in labels:
        return "mixed_synthetic_and_observed"
    if labels & {DataLabel.OBSERVED.value, DataLabel.REAL.value, "observed", "real"}:
        return "realtime_screening"
    return "modelled_screening"


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

    # Data sources status with true freshness from latest signal ingest
    src_res = await db.execute(select(DataSource).where(DataSource.tenant_id == tenant_id))
    sources = src_res.scalars().all()

    latest_by_source = dict(
        (
            await db.execute(
                select(SignalRecord.source_id, func.max(SignalRecord.ingested_at))
                .where(SignalRecord.tenant_id == tenant_id)
                .group_by(SignalRecord.source_id)
            )
        ).all()
    )
    latest_ingest = max(latest_by_source.values()) if latest_by_source else None

    source_health_list = []
    online = 0
    for s in sources:
        last_seen = latest_by_source.get(s.id) or s.updated_at
        status, age = classify_freshness(last_seen, s.freshness_threshold_minutes)
        if s.is_active and status == "fresh":
            online += 1
        source_health_list.append(
            SourceHealth(
                id=s.id,
                name=s.name,
                signal_family=s.signal_family.value,
                status=status,
                freshness_minutes=age,
                threshold_minutes=s.freshness_threshold_minutes or 180,
                last_received_at=last_seen,
            )
        )

    data_mode = await _resolve_data_mode(db, tenant_id)

    return OverviewResponse(
        active_alert_count=len(alerts),
        severity_breakdown=severity_breakdown,
        pending_task_count=pending_tasks,
        sources_online_count=online,
        total_sources_count=len(sources),
        last_update_at=latest_ingest or datetime.now(timezone.utc),
        active_episodes=active_episodes,
        sources=source_health_list,
        data_mode=data_mode,
    )
