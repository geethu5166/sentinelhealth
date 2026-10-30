"""Unit and service tests for ingestion, alert, and task execution idempotency."""

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.detectors.ewma import OneSidedEWMADetector
from app.analytics.fusion.policy import EvidenceFusionEngine, EvidenceItem, FusionDecision
from app.alerts.service import AlertService
from app.connectors.base import NormalizedRecord
from app.ingestion.service import IngestionService
from app.models.alert import Alert, AlertStatus, Hazard, AlertSeverity, EvidenceClass
from app.models.playbook import Playbook, PlaybookApprovalStatus, PreventiveTask, TaskStatus
from app.models.signal import DataSource, IngestionRun, SignalFamily, SignalRecord, SourceType
from app.models.tenant import Tenant
from app.playbooks.service import PlaybookService


@pytest.mark.asyncio
async def test_ingestion_idempotency_run_key(db_session: AsyncSession):
    """Re-running ingestion with identical idempotency key returns existing run without duplicate records."""
    # 1. Fetch tenant
    t_res = await db_session.execute(select(Tenant).where(Tenant.slug == "district_health_authority"))
    tenant = t_res.scalar_one()

    # 2. Create DataSource
    source = DataSource(
        tenant_id=tenant.id,
        name="District Clinic Test Feed",
        code=f"clinic-test-{uuid.uuid4().hex[:8]}",
        signal_family=SignalFamily.CLINICAL_SERVICE,
        source_type=SourceType.CONNECTOR,
        schema_version="1.0.0",
        is_active=True,
    )
    db_session.add(source)
    await db_session.flush()

    service = IngestionService(db_session)
    now = datetime.now(timezone.utc)
    records = [
        NormalizedRecord(
            source_record_id=f"rec-{uuid.uuid4().hex[:8]}",
            metric_code="heat_exhaustion_contacts",
            signal_family="clinical_service",
            value=12.0,
            unit="contacts",
            period_start=now - timedelta(days=1),
            period_end=now,
            observed_at=now,
            source_available_at=now,
            data_label="synthetic",
        )
    ]

    idempotency_key = f"key-{uuid.uuid4().hex}"

    # First run
    run1 = await service.run_ingestion(tenant.id, source, records, idempotency_key=idempotency_key)
    assert run1.records_accepted == 1

    # Second run with same idempotency key
    run2 = await service.run_ingestion(tenant.id, source, records, idempotency_key=idempotency_key)
    assert run2.id == run1.id

    # Verify no duplicate signal records were added
    count_res = await db_session.execute(
        select(SignalRecord).where(SignalRecord.source_id == source.id)
    )
    all_recs = count_res.scalars().all()
    assert len(all_recs) == 1


@pytest.mark.asyncio
async def test_alert_episode_deduplication(db_session: AsyncSession):
    """Subsequent detections within 72h window update existing episode rather than creating duplicate alerts."""
    t_res = await db_session.execute(select(Tenant).where(Tenant.slug == "district_health_authority"))
    tenant = t_res.scalar_one()

    alert_service = AlertService(db_session)
    geo_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    decision1 = FusionDecision(
        hazard="heat_illness",
        severity="watch",
        evidence_class="environmental_watch",
        evidence_score=45.0,
        should_alert=True,
        reasons=["High apparent temperature"],
        missing_families=[],
        contributing_evidences=[],
        policy_version="0.1.0",
    )

    alert1 = await alert_service.create_or_update_alert(
        tenant_id=tenant.id,
        decision=decision1,
        geography_id=geo_id,
        target_period_start=now - timedelta(hours=2),
        target_period_end=now,
        responsible_role="public_health_analyst",
        episode_window_hours=72,
    )
    await db_session.commit()

    # Re-evaluation / update detection 1 hour later
    decision2 = FusionDecision(
        hazard="heat_illness",
        severity="warning",
        evidence_class="corroborated_health_warning",
        evidence_score=82.0,
        should_alert=True,
        reasons=["High temperature corroborated by clinical contacts"],
        missing_families=[],
        contributing_evidences=[],
        policy_version="0.1.0",
    )

    alert2 = await alert_service.create_or_update_alert(
        tenant_id=tenant.id,
        decision=decision2,
        geography_id=geo_id,
        target_period_start=now - timedelta(hours=1),
        target_period_end=now + timedelta(hours=1),
        responsible_role="public_health_analyst",
        episode_window_hours=72,
    )
    await db_session.commit()

    # Both calls should resolve to the exact same alert episode ID
    assert alert2.id == alert1.id
    assert alert2.severity == AlertSeverity.WARNING
    assert alert2.evidence_score == Decimal("82.0")

    # Verify database only contains 1 alert for this episode
    all_alerts_res = await db_session.execute(
        select(Alert).where(Alert.tenant_id == tenant.id, Alert.episode_key == alert1.episode_key)
    )
    assert len(all_alerts_res.scalars().all()) == 1


@pytest.mark.asyncio
async def test_preventive_task_idempotency(db_session: AsyncSession):
    """Re-generating tasks for an alert with an active task does not create duplicates."""
    t_res = await db_session.execute(select(Tenant).where(Tenant.slug == "district_health_authority"))
    tenant = t_res.scalar_one()

    # 1. Create Playbook
    playbook = Playbook(
        hazard="heat_illness",
        jurisdiction="demo_fictional",
        sector="public_health",
        version="1.0.0",
        approval_status=PlaybookApprovalStatus.APPROVED,
        action_tiers={
            "tier_1_preparation": {
                "title": "Public Hydration Advisory",
                "action": "Issue heat advisory to vulnerable populations",
                "accountable_role": "public_health_analyst",
                "review_window_hours": 24,
            }
        },
    )
    db_session.add(playbook)

    # 2. Create Alert
    now = datetime.now(timezone.utc)
    alert = Alert(
        tenant_id=tenant.id,
        hazard=Hazard.HEAT_ILLNESS,
        evidence_class=EvidenceClass.ENVIRONMENTAL_WATCH,
        severity=AlertSeverity.WATCH,
        status=AlertStatus.NEW,
        geography_id=uuid.uuid4(),
        target_period_start=now,
        target_period_end=now + timedelta(hours=24),
        first_detected_at=now,
        latest_revision_at=now,
        episode_key=f"{tenant.id}:heat_illness:geo-{uuid.uuid4().hex[:6]}",
        responsible_role="public_health_analyst",
        evidence_score=Decimal("0.50"),
    )
    db_session.add(alert)
    await db_session.flush()

    playbook_service = PlaybookService(db_session)

    # First call creates task
    rec1, task1 = await playbook_service.generate_recommendation_and_task(alert, playbook)
    assert task1.status == TaskStatus.PENDING

    # Second call for the same alert
    rec2, task2 = await playbook_service.generate_recommendation_and_task(alert, playbook)

    # Must return the existing task, NOT create a second task
    assert task2.id == task1.id

    # Verify only 1 task exists for this alert in the database
    tasks_res = await db_session.execute(
        select(PreventiveTask).where(PreventiveTask.alert_id == alert.id)
    )
    assert len(tasks_res.scalars().all()) == 1


@pytest.mark.asyncio
async def test_repeated_detection_evaluation_idempotency(db_session: AsyncSession):
    """Verifies that repeated detection evaluations against unchanged observation data
    do NOT advance detector state (EWMA / statistics remain invariant) or create duplicate alert records."""
    t_res = await db_session.execute(select(Tenant).where(Tenant.slug == "district_health_authority"))
    tenant = t_res.scalar_one()

    detector = OneSidedEWMADetector(smoothing_factor=0.3, control_limit_sigma=2.5, min_observations=3)
    fusion_engine = EvidenceFusionEngine(policy_version="0.1.0")
    alert_service = AlertService(db_session)

    geo_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    target_start = now - timedelta(hours=2)
    target_end = now

    # Initial history of standardised residuals
    historical_residuals = [1.2, 1.5, 1.8]
    observed_val = 35.0
    expected_val = 20.0
    se = 3.0

    # 1. Run detection evaluation 1st time
    score1 = detector.compute_anomaly(
        observed=observed_val,
        expected=expected_val,
        standard_error=se,
        historical_residuals=historical_residuals,
    )

    # 2. Run detection evaluation 2nd time on identical, unchanged observation data
    score2 = detector.compute_anomaly(
        observed=observed_val,
        expected=expected_val,
        standard_error=se,
        historical_residuals=historical_residuals,
    )

    # Verify detector state did not advance or drift
    assert score1.ewma_value == score2.ewma_value
    assert score1.standardised_residual == score2.standardised_residual
    assert score1.ewma_threshold == score2.ewma_threshold
    assert score1.is_anomaly == score2.is_anomaly
    assert score1.is_sustained == score2.is_sustained
    assert score1.severity_level == score2.severity_level
    assert score1.details["history_length"] == score2.details["history_length"]
    assert score1.details["step_number"] == score2.details["step_number"]
    assert historical_residuals == [1.2, 1.5, 1.8]

    # 3. Fuse evidence and trigger alert service
    ev1 = EvidenceItem(
        signal_family="clinical_service",
        metric_code="heat_exhaustion_contacts",
        observed=observed_val,
        expected=expected_val,
        excess=score1.excess,
        standardised_residual=score1.standardised_residual,
        ewma_value=score1.ewma_value,
        is_anomaly=score1.is_anomaly,
        source_freshness_minutes=15,
        is_fresh=True,
        is_stale=False,
        data_label="synthetic",
        geography_id=str(geo_id),
        timestamp=now,
    )
    decision1 = fusion_engine.evaluate(
        hazard="heat_illness",
        evidences=[ev1],
        environmental_thresholds={},
    )
    decision2 = fusion_engine.evaluate(
        hazard="heat_illness",
        evidences=[ev1],
        environmental_thresholds={},
    )
    assert decision1 == decision2

    # First alert evaluation
    alert1 = await alert_service.create_or_update_alert(
        tenant_id=tenant.id,
        decision=decision1,
        geography_id=geo_id,
        target_period_start=target_start,
        target_period_end=target_end,
        responsible_role="public_health_analyst",
        episode_window_hours=72,
    )
    await db_session.commit()

    # Second alert evaluation with identical unchanged detection result
    alert2 = await alert_service.create_or_update_alert(
        tenant_id=tenant.id,
        decision=decision2,
        geography_id=geo_id,
        target_period_start=target_start,
        target_period_end=target_end,
        responsible_role="public_health_analyst",
        episode_window_hours=72,
    )
    await db_session.commit()

    # Verify alert deduplication: same instance returned
    assert alert2.id == alert1.id
    assert alert2.episode_key == alert1.episode_key

    # Verify no duplicate alert records were inserted into the DB
    alerts_res = await db_session.execute(
        select(Alert).where(Alert.tenant_id == tenant.id, Alert.episode_key == alert1.episode_key)
    )
    records = alerts_res.scalars().all()
    assert len(records) == 1
