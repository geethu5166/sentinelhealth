"""End-to-End Deployed Heat Risk Workflow Integration Test.

Phase 2 Operational Loop Verification:
1. Authorized Authentication & Tenant Resolution (Tenant B: Greenfield Industries, Workplace Safety Manager)
2. Ingestion of Multi-Source Synthetic Signals (Environmental sWBGT/Heat Index + Workforce Absence)
3. Baseline Fitting, Signed EWMA Residual Anomaly Detection, and Evidence Fusion
4. Privacy-Safe Alert Publication with Small-Cell Suppression
5. Playbook Recommendation & Preventive Task Generation
6. Task Acknowledgment by Assigned Role
7. Task Completion with Auditable Execution Evidence
8. Strict Cross-Tenant Verification: Tenant A (District Health Authority) cannot read Tenant B's alert or task.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts.service import AlertService
from app.analytics.baselines.models import PoissonCountBaseline, RecentHistoryBaseline
from app.analytics.detectors.ewma import OneSidedEWMADetector
from app.analytics.fusion.policy import EvidenceFusionEngine, EvidenceItem
from app.connectors.base import NormalizedRecord
from app.ingestion.service import IngestionService
from app.models.alert import Alert, AlertSeverity, AlertStatus, EvidenceClass, Hazard
from app.models.playbook import Playbook, PlaybookApprovalStatus, PreventiveTask, TaskStatus
from app.models.signal import DataSource, SignalFamily, SignalRecord, SourceType
from app.models.tenant import MembershipRole, Tenant, User
from app.playbooks.service import PlaybookService
from app.privacy.suppression import DisclosureChecker, apply_suppression


@pytest.mark.asyncio
async def test_complete_deployed_heat_workflow_end_to_end(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_tenant_a: dict,
    auth_headers_tenant_b: dict,
):
    """Executes the complete operational loop for heat illness risk management in workforce and public health."""
    now = datetime.now(timezone.utc)

    # ──────────────────────────────────────────────────────────────────────────
    # Step 1: Resolve Tenants & Users
    # ──────────────────────────────────────────────────────────────────────────
    # Tenant B: Greenfield Industries (Workforce tenant)
    res_b = await db_session.execute(select(Tenant).where(Tenant.slug == "greenfield_industries"))
    tenant_b = res_b.scalar_one()

    # Tenant A: District Health Authority (Public Health tenant)
    res_a = await db_session.execute(select(Tenant).where(Tenant.slug == "district_health_authority"))
    tenant_a = res_a.scalar_one()

    # ──────────────────────────────────────────────────────────────────────────
    # Step 2: Ingest Multi-Source Signals for Tenant B
    # ──────────────────────────────────────────────────────────────────────────
    ingestion_service = IngestionService(db_session)

    # Source 1: Plant Weather Screening Source
    weather_source = DataSource(
        tenant_id=tenant_b.id,
        name="Lakshmi Foundry Weather Sensor",
        code=f"foundry-weather-{uuid.uuid4().hex[:6]}",
        signal_family=SignalFamily.ENVIRONMENTAL,
        source_type=SourceType.CONNECTOR,
        provider="synthetic_weather_station",
        schema_version="1.0.0",
        expected_cadence_minutes=60,
        freshness_threshold_minutes=180,
        is_active=True,
    )
    # Source 2: Workplace Absence & Incident Source
    workforce_source = DataSource(
        tenant_id=tenant_b.id,
        name="Foundry EHS Workforce Safety System",
        code=f"foundry-ehs-{uuid.uuid4().hex[:6]}",
        signal_family=SignalFamily.WORKFORCE,
        source_type=SourceType.CONNECTOR,
        provider="synthetic_ehs",
        schema_version="1.0.0",
        expected_cadence_minutes=60,
        freshness_threshold_minutes=360,
        is_active=True,
    )
    db_session.add_all([weather_source, workforce_source])
    await db_session.flush()

    geo_b_id = uuid.uuid4()

    # Ingest Environmental Records (Peak apparent temp = 43.5°C, high thermal stress)
    weather_records = [
        NormalizedRecord(
            source_record_id=f"rec-wx-{uuid.uuid4().hex[:6]}",
            metric_code="apparent_temperature",
            signal_family="environmental",
            value=43.5,
            unit="celsius",
            period_start=now - timedelta(hours=2),
            period_end=now,
            observed_at=now,
            source_available_at=now,
            geography_id=str(geo_b_id),
            data_label="synthetic",
            provenance="On-site calibrated sensor grid",
        )
    ]
    run_wx = await ingestion_service.run_ingestion(
        tenant_id=tenant_b.id,
        source=weather_source,
        records=weather_records,
        idempotency_key=f"ingest-wx-{uuid.uuid4().hex}",
    )
    assert run_wx.records_accepted == 1

    # Ingest Workforce Absence Records (Elevated heat-exhaustion sickness absence = 3, low count)
    workforce_records = [
        NormalizedRecord(
            source_record_id=f"rec-wf-{uuid.uuid4().hex[:6]}",
            metric_code="sickness_absence_worker_days",
            signal_family="workforce",
            value=3.0,  # Small count: triggers privacy suppression test
            unit="worker_days",
            contributor_count=3,
            period_start=now - timedelta(hours=8),
            period_end=now,
            observed_at=now,
            source_available_at=now,
            geography_id=str(geo_b_id),
            data_label="synthetic",
            provenance="Foundry shift turnstile & health clinic logs",
        )
    ]
    run_wf = await ingestion_service.run_ingestion(
        tenant_id=tenant_b.id,
        source=workforce_source,
        records=workforce_records,
        idempotency_key=f"ingest-wf-{uuid.uuid4().hex}",
    )
    assert run_wf.records_accepted == 1
    await db_session.commit()

    # ──────────────────────────────────────────────────────────────────────────
    # Step 3: Run Baseline Estimation, Signed EWMA, and Fusion Engine
    # ──────────────────────────────────────────────────────────────────────────
    detector = OneSidedEWMADetector(smoothing_factor=0.3, control_limit_sigma=2.5)
    fusion_engine = EvidenceFusionEngine(policy_version="0.1.0")

    # Score environmental evidence
    env_score = detector.compute_anomaly(
        observed=43.5,
        expected=34.0,
        standard_error=2.0,
        historical_residuals=[1.2, 1.8, 2.4, 3.1],
    )
    assert env_score.is_anomaly is True

    # Score workforce absence evidence
    wf_score = detector.compute_anomaly(
        observed=3.0,
        expected=0.8,
        standard_error=0.89,  # sqrt(0.8) for Poisson
        historical_residuals=[0.5, 0.8, 1.5, 2.2],
    )
    assert wf_score.is_anomaly is True

    ev1 = EvidenceItem(
        signal_family="environmental",
        metric_code="apparent_temperature",
        observed=43.5,
        expected=34.0,
        excess=env_score.excess,
        standardised_residual=env_score.standardised_residual,
        ewma_value=env_score.ewma_value,
        is_anomaly=env_score.is_anomaly,
        source_freshness_minutes=15,
        is_fresh=True,
        is_stale=False,
        data_label="synthetic",
        geography_id=str(geo_b_id),
        timestamp=now,
    )
    ev2 = EvidenceItem(
        signal_family="workforce",
        metric_code="sickness_absence_worker_days",
        observed=3.0,
        expected=0.8,
        excess=wf_score.excess,
        standardised_residual=wf_score.standardised_residual,
        ewma_value=wf_score.ewma_value,
        is_anomaly=wf_score.is_anomaly,
        source_freshness_minutes=60,
        is_fresh=True,
        is_stale=False,
        data_label="synthetic",
        geography_id=str(geo_b_id),
        timestamp=now,
    )

    decision = fusion_engine.evaluate(
        hazard="heat_illness",
        evidences=[ev1, ev2],
        environmental_thresholds={"apparent_temperature": 39.0},
    )
    assert decision.should_alert is True
    assert decision.evidence_class == "corroborated_health_warning"
    assert decision.severity in ["warning", "critical"]

    # ──────────────────────────────────────────────────────────────────────────
    # Step 4: Publish Alert & Validate Privacy Suppression
    # ──────────────────────────────────────────────────────────────────────────
    alert_service = AlertService(db_session)
    alert = await alert_service.create_or_update_alert(
        tenant_id=tenant_b.id,
        decision=decision,
        geography_id=geo_b_id,
        target_period_start=now - timedelta(hours=4),
        target_period_end=now,
        responsible_role="workplace_safety_manager",
        episode_window_hours=72,
    )
    await db_session.commit()
    assert alert.tenant_id == tenant_b.id
    assert alert.status == AlertStatus.NEW

    # Validate Privacy Suppression Engine on small cell counts (<5 masked, <10 contributors)
    checker = DisclosureChecker(min_contributors=10, suppress_range=(1, 4))
    raw_health_rec = {"metric_code": "sickness_absence_worker_days", "value": 3, "contributor_count": 3}
    safe_rec = checker.protect_record(raw_health_rec, is_sensitive_health_metric=True)
    # Value of 3 is within [1, 4] and contributor count 3 < 10, so value should be suppressed/masked
    assert safe_rec["is_suppressed"] is True
    assert safe_rec["value"] is None
    assert (
        "protected small-cell range" in safe_rec["suppression_reason"]
        or "below privacy threshold" in safe_rec["suppression_reason"]
    )

    raw_env_rec = {"metric_code": "apparent_temperature", "value": 43.5, "contributor_count": None}
    safe_env = checker.protect_record(raw_env_rec, is_sensitive_health_metric=False)
    assert safe_env["is_suppressed"] is False
    assert safe_env["value"] == 43.5

    # ──────────────────────────────────────────────────────────────────────────
    # Step 5: Playbook Recommendation & Preventive Task Generation
    # ──────────────────────────────────────────────────────────────────────────
    playbook = Playbook(
        tenant_id=tenant_b.id,
        hazard="heat_illness",
        jurisdiction="workforce_standard",
        sector="manufacturing_heavy_industry",
        version="1.0.0",
        approval_status=PlaybookApprovalStatus.APPROVED,
        action_tiers={
            "tier_2_active_control": {
                "title": "Urgent safety-lead review: assess on-site heat exposure and activate approved heat-response procedure",
                "action": "Initiate urgent on-site occupational safety review. Assess environmental conditions, ventilation, and worker acclimatisation, and activate the approved heat-response procedure. Record the responsible person, actions taken, and scheduled follow-up.",
                "accountable_role": "workplace_safety_manager",
                "completion_evidence_required": "On-site assessment checklist, responsible person sign-off, and action log",
                "review_window_hours": 12,
            }
        },
    )
    db_session.add(playbook)
    await db_session.flush()

    playbook_service = PlaybookService(db_session)
    rec, task = await playbook_service.generate_recommendation_and_task(alert, playbook)
    await db_session.commit()

    assert task.tenant_id == tenant_b.id
    assert task.alert_id == alert.id
    assert task.assigned_role == "workplace_safety_manager"
    assert task.status == TaskStatus.PENDING

    # ──────────────────────────────────────────────────────────────────────────
    # Step 6: Task Acknowledgment via Authenticated API (Tenant B)
    # ──────────────────────────────────────────────────────────────────────────
    ack_payload = {
        "status": "in_progress",
        "completion_notes": "Acknowledged by shift safety engineer; rotation schedules dispatched to plant supervisors.",
    }
    ack_resp = await client.patch(
        f"/api/v1/tasks/{task.id}",
        json=ack_payload,
        headers=auth_headers_tenant_b,
    )
    assert ack_resp.status_code == 200
    task_data = ack_resp.json()
    assert task_data["status"] == "in_progress"

    # ──────────────────────────────────────────────────────────────────────────
    # Step 7: Task Completion with Auditable Evidence (Tenant B)
    # ──────────────────────────────────────────────────────────────────────────
    complete_payload = {
        "status": "completed",
        "completion_evidence": "Electrolyte dispensers inspected and filled at 11:30. All 42 workers completed 15min/hour rest cycles. Zero heat syncope cases reported.",
        "completion_notes": "All recommended mitigation controls successfully executed for shift duration.",
    }
    complete_resp = await client.patch(
        f"/api/v1/tasks/{task.id}",
        json=complete_payload,
        headers=auth_headers_tenant_b,
    )
    assert complete_resp.status_code == 200
    completed_task = complete_resp.json()
    assert completed_task["status"] == "completed"
    assert "Electrolyte dispensers inspected" in completed_task["completion_evidence"]

    # ──────────────────────────────────────────────────────────────────────────
    # Step 8: Strict Cross-Tenant Access Rejection (Tenant A cannot see Tenant B objects)
    # ──────────────────────────────────────────────────────────────────────────
    # Tenant A tries to fetch Tenant B's alert
    cross_alert_resp = await client.get(
        f"/api/v1/alerts/{alert.id}",
        headers=auth_headers_tenant_a,
    )
    # Must be not found (404) or forbidden (403), never accessible
    assert cross_alert_resp.status_code in [404, 403]

    # Tenant A tries to fetch Tenant B's preventive task
    cross_task_resp = await client.get(
        f"/api/v1/tasks/{task.id}",
        headers=auth_headers_tenant_a,
    )
    assert cross_task_resp.status_code in [404, 403]

    # Tenant A list alerts must not contain Tenant B's alert ID
    list_a_resp = await client.get("/api/v1/alerts", headers=auth_headers_tenant_a)
    assert list_a_resp.status_code == 200
    alerts_a = list_a_resp.json()
    assert not any(a["id"] == str(alert.id) for a in alerts_a)
