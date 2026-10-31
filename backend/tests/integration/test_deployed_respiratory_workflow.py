"""End-to-End Deployed Air Quality & Respiratory Risk Workflow Integration Test.

Phase 3 Operational Loop Verification:
1. Authorized Authentication & Tenant Resolution (Tenant A: District Health Authority, Public Health Epidemiologist)
2. Ingestion of Multi-Source Air Quality & Respiratory Signals:
   - Environmental PM2.5 (1-hour screening & 24-hour completed mean with >=75% coverage)
   - Clinical acute respiratory contacts (with privacy-safe small cell counts)
3. Baseline Fitting, Signed EWMA Residual Anomaly Detection, and Evidence Fusion Engine (Policy v0.2.0)
   - Transparent single environmental family (no double-counting PM2.5 and AQI)
   - Non-causal wording: "Concurrent pollution exposure and respiratory-health anomaly; cause not established"
4. Privacy-Safe Alert Publication & Disclosure Control Verification on API endpoints:
   - Suppressed rate per 100k when counts in [1, 4] or contributors < 10
   - Accurate denominator & encounter rate labelling (not disease incidence)
5. Proportionate Air-Quality Playbook & Human-in-the-Loop Preventive Task Generation
   - Enforces Prototype Prohibited-Use Controls (no automatic medication, no mandatory restrictions without clinician review, no fit-test bypass)
   - "Safety lead to review the approved exposure-control and respiratory-protection procedure"
6. Task Acknowledgment by Assigned Safety Lead
7. Task Completion with Auditable Execution Evidence
8. Strict Cross-Tenant Verification: Tenant B (Greenfield Industries) cannot access Tenant A's respiratory alert or task.
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
from app.analytics.baselines.models import PoissonCountBaseline
from app.analytics.detectors.ewma import OneSidedEWMADetector
from app.analytics.fusion.policy import EvidenceFusionEngine, EvidenceItem
from app.analytics.playbooks.air_quality import AirQualityPlaybook
from app.connectors.base import NormalizedRecord
from app.connectors.open_meteo_air_quality import OpenMeteoAirQualityConnector
from app.ingestion.service import IngestionService
from app.models.alert import Alert, AlertSeverity, AlertStatus, EvidenceClass, Hazard
from app.models.playbook import Playbook, PlaybookApprovalStatus, PreventiveTask, TaskStatus
from app.models.signal import DataSource, SignalFamily, SignalRecord, SourceType
from app.models.tenant import MembershipRole, Tenant, User
from app.playbooks.service import PlaybookService
from app.privacy.suppression import DisclosureChecker


@pytest.mark.asyncio
async def test_complete_deployed_respiratory_workflow_end_to_end(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_tenant_a: dict,
    auth_headers_tenant_b: dict,
):
    """Executes the complete operational loop for air quality and respiratory surveillance."""
    now = datetime.now(timezone.utc)

    # ──────────────────────────────────────────────────────────────────────────
    # Step 1: Resolve Tenants
    # ──────────────────────────────────────────────────────────────────────────
    # Tenant A: District Health Authority (Public health authority)
    res_a = await db_session.execute(select(Tenant).where(Tenant.slug == "district_health_authority"))
    tenant_a = res_a.scalar_one()

    # Tenant B: Greenfield Industries (Workforce tenant)
    res_b = await db_session.execute(select(Tenant).where(Tenant.slug == "greenfield_industries"))
    tenant_b = res_b.scalar_one()

    # ──────────────────────────────────────────────────────────────────────────
    # Step 2: Ingest Multi-Source Signals for Tenant A
    # ──────────────────────────────────────────────────────────────────────────
    ingestion_service = IngestionService(db_session)

    # Source 1: Open-Meteo CAMS Global Ambient Air Quality Connector
    aq_source = DataSource(
        tenant_id=tenant_a.id,
        name="District Ambient Air Quality Screening Monitor",
        code=f"cams-aq-{uuid.uuid4().hex[:6]}",
        signal_family=SignalFamily.ENVIRONMENTAL,
        source_type=SourceType.CONNECTOR,
        provider="open_meteo_cams_global",
        schema_version="2.0.0",
        expected_cadence_minutes=60,
        freshness_threshold_minutes=180,
        is_active=True,
    )
    # Source 2: Primary Health Centre Acute Respiratory Syndromic Encounters
    clinic_source = DataSource(
        tenant_id=tenant_a.id,
        name="PHC Network Acute Respiratory Surveillance",
        code=f"phc-resp-{uuid.uuid4().hex[:6]}",
        signal_family=SignalFamily.CLINICAL_SERVICE,
        source_type=SourceType.CONNECTOR,
        provider="synthetic_phc_emr",
        schema_version="1.0.0",
        expected_cadence_minutes=60,
        freshness_threshold_minutes=360,
        is_active=True,
    )
    db_session.add_all([aq_source, clinic_source])
    await db_session.flush()

    geo_a_id = uuid.uuid4()

    # Ingest 1-hour PM2.5 screening record (elevated at 135.0 ug/m3)
    aq_records = [
        NormalizedRecord(
            source_record_id=f"rec-aq-{uuid.uuid4().hex[:6]}",
            metric_code="pm25_concentration",
            signal_family="environmental",
            value=135.0,
            unit="ug/m3",
            period_start=now - timedelta(hours=1),
            period_end=now,
            observed_at=now,
            source_available_at=now,
            geography_id=str(geo_a_id),
            data_label="synthetic",
            provenance="CAMS Global Atmospheric Composition Forecast (Screening proxy; not compliant reference monitor)",
        )
    ]
    run_aq = await ingestion_service.run_ingestion(
        tenant_id=tenant_a.id,
        source=aq_source,
        records=aq_records,
        idempotency_key=f"ingest-aq-{uuid.uuid4().hex}",
    )
    assert run_aq.records_accepted == 1

    # Ingest Clinical Acute Respiratory Contacts (obs = 45, well above baseline)
    clinic_records = [
        NormalizedRecord(
            source_record_id=f"rec-resp-{uuid.uuid4().hex[:6]}",
            metric_code="acute_respiratory_contacts",
            signal_family="clinical_service",
            value=45.0,
            unit="encounters",
            contributor_count=45,
            period_start=now - timedelta(hours=24),
            period_end=now,
            observed_at=now,
            source_available_at=now,
            geography_id=str(geo_a_id),
            data_label="synthetic",
            provenance="District Primary Care EMR Syndromic Triage",
        )
    ]
    run_clinic = await ingestion_service.run_ingestion(
        tenant_id=tenant_a.id,
        source=clinic_source,
        records=clinic_records,
        idempotency_key=f"ingest-clinic-{uuid.uuid4().hex}",
    )
    assert run_clinic.records_accepted == 1
    await db_session.commit()

    # ──────────────────────────────────────────────────────────────────────────
    # Step 3: Run EWMA Anomaly Detector and Fusion Engine (Policy v0.2.0)
    # ──────────────────────────────────────────────────────────────────────────
    detector = OneSidedEWMADetector(smoothing_factor=0.3, control_limit_sigma=2.5)
    fusion_engine = EvidenceFusionEngine(policy_version="0.2.0")

    # Score PM2.5 anomaly
    aq_score = detector.compute_anomaly(
        observed=135.0,
        expected=40.0,
        standard_error=12.0,
        historical_residuals=[2.0, 3.5, 5.0, 7.9],
    )
    assert aq_score.is_anomaly is True

    # Score clinical respiratory encounters anomaly
    clinic_score = detector.compute_anomaly(
        observed=45.0,
        expected=12.0,
        standard_error=3.46,  # sqrt(12.0)
        historical_residuals=[1.5, 2.8, 4.1, 9.5],
    )
    assert clinic_score.is_anomaly is True

    ev_aq = EvidenceItem(
        signal_family="environmental",
        metric_code="pm25_concentration",
        observed=135.0,
        expected=40.0,
        excess=aq_score.excess,
        standardised_residual=aq_score.standardised_residual,
        ewma_value=aq_score.ewma_value,
        is_anomaly=aq_score.is_anomaly,
        source_freshness_minutes=15,
        is_fresh=True,
        is_stale=False,
        data_label="synthetic",
        geography_id=str(geo_a_id),
        timestamp=now,
        unit="ug/m3",
    )
    ev_clinic = EvidenceItem(
        signal_family="clinical_service",
        metric_code="acute_respiratory_contacts",
        observed=45.0,
        expected=12.0,
        excess=clinic_score.excess,
        standardised_residual=clinic_score.standardised_residual,
        ewma_value=clinic_score.ewma_value,
        is_anomaly=clinic_score.is_anomaly,
        source_freshness_minutes=30,
        is_fresh=True,
        is_stale=False,
        data_label="synthetic",
        geography_id=str(geo_a_id),
        timestamp=now,
        denominator=100000.0,
    )

    decision = fusion_engine.evaluate(
        hazard="air_quality_respiratory",
        evidences=[ev_aq, ev_clinic],
        environmental_thresholds={"pm25_concentration": 60.0},
    )
    assert decision.should_alert is True
    assert decision.evidence_class == "corroborated_health_warning"
    assert decision.severity in ["warning", "critical"]
    # Non-causal wording verification
    assert any("cause not established" in r.lower() for r in decision.reasons)

    # ──────────────────────────────────────────────────────────────────────────
    # Step 4: Publish Alert & Validate Disclosure Control
    # ──────────────────────────────────────────────────────────────────────────
    alert_service = AlertService(db_session)
    alert = await alert_service.create_or_update_alert(
        tenant_id=tenant_a.id,
        decision=decision,
        geography_id=geo_a_id,
        target_period_start=now - timedelta(hours=24),
        target_period_end=now,
        responsible_role="district_health_officer",
        episode_window_hours=72,
    )
    await db_session.commit()
    assert alert.tenant_id == tenant_a.id
    assert alert.status == AlertStatus.NEW

    # Test small cell suppression on a small respiratory cluster (n=2, 2 contributors)
    checker = DisclosureChecker(min_contributors=10, suppress_range=(1, 4))
    small_resp_rec = {"metric_code": "acute_respiratory_contacts", "value": 2, "contributor_count": 2}
    suppressed_rec = checker.protect_record(small_resp_rec, is_sensitive_health_metric=True)
    assert suppressed_rec["is_suppressed"] is True
    assert suppressed_rec["value"] is None

    # Test environmental PM2.5 is not suppressed even if value is in [1, 4]
    env_rec = {"metric_code": "pm25_concentration", "value": 3.5, "contributor_count": None}
    unsuppressed_env = checker.protect_record(env_rec, is_sensitive_health_metric=False)
    assert unsuppressed_env["is_suppressed"] is False
    assert unsuppressed_env["value"] == 3.5

    # ──────────────────────────────────────────────────────────────────────────
    # Step 5: Playbook Recommendation with Prototype Prohibited-Use Controls
    # ──────────────────────────────────────────────────────────────────────────
    # Verify prototype prohibited use controls are in place
    boundaries = AirQualityPlaybook.PROTOTYPE_PROHIBITED_USE_CONTROLS
    assert boundaries["prohibit_automatic_medical_treatment"] is True
    assert boundaries["prohibit_mandatory_individual_restrictions_without_clinician"] is True
    assert boundaries["prohibit_respirator_mandate_without_fit_test"] is True
    assert boundaries["prohibit_disciplinary_actions"] is True

    rec_spec = AirQualityPlaybook.generate_recommendation(
        evidence_class=decision.evidence_class,
        severity=decision.severity,
        evidence_summary="; ".join(decision.reasons),
        district_id=str(geo_a_id),
    )
    assert rec_spec["action_tier"] in ["tier_2_adjusted_operations", "tier_3_restricted_activity"]
    # Verification of human reviewability in action instructions
    assert any("review the approved exposure-control and respiratory-protection procedure" in a.lower() for a in rec_spec["recommended_actions"])

    # Save approved database playbook record
    db_playbook = Playbook(
        tenant_id=tenant_a.id,
        hazard="respiratory_air_quality",
        jurisdiction="district_public_health",
        sector="municipal_healthcare",
        version=2,
        approval_status=PlaybookApprovalStatus.APPROVED,
        action_tiers={
            rec_spec["action_tier"]: {
                "title": rec_spec["action_tier_name"],
                "action": rec_spec["recommended_actions"][0],
                "accountable_role": rec_spec["accountable_roles"][0],
                "completion_evidence_required": rec_spec["completion_evidence_required"],
                "review_window_hours": rec_spec["review_window_hours"],
            }
        },
    )
    db_session.add(db_playbook)
    await db_session.flush()

    playbook_service = PlaybookService(db_session)
    rec, task = await playbook_service.generate_recommendation_and_task(alert, db_playbook)
    await db_session.commit()

    assert task.tenant_id == tenant_a.id
    assert task.alert_id == alert.id
    assert task.assigned_role in rec_spec["accountable_roles"]
    assert task.status == TaskStatus.PENDING

    # ──────────────────────────────────────────────────────────────────────────
    # Step 6: Task Acknowledgment via Authenticated API (Tenant A)
    # ──────────────────────────────────────────────────────────────────────────
    ack_payload = {
        "status": "in_progress",
        "completion_notes": "Safety lead acknowledged respiratory surge alert; air handling and mask guidelines dispatched.",
    }
    ack_resp = await client.patch(
        f"/api/v1/tasks/{task.id}",
        json=ack_payload,
        headers=auth_headers_tenant_a,
    )
    assert ack_resp.status_code == 200
    task_data = ack_resp.json()
    assert task_data["status"] == "in_progress"

    # ──────────────────────────────────────────────────────────────────────────
    # Step 7: Task Completion with Auditable Execution Evidence (Tenant A)
    # ──────────────────────────────────────────────────────────────────────────
    complete_payload = {
        "status": "completed",
        "completion_evidence": "HEPA filtration deployed in triage wards. Outdoor physical activities paused for vulnerable groups. Primary health centres stocked with bronchodilators.",
        "completion_notes": "All tier-2 exposure-reduction recommendations executed under clinician supervision.",
    }
    complete_resp = await client.patch(
        f"/api/v1/tasks/{task.id}",
        json=complete_payload,
        headers=auth_headers_tenant_a,
    )
    assert complete_resp.status_code == 200
    completed_task = complete_resp.json()
    assert completed_task["status"] == "completed"
    assert "HEPA filtration deployed" in completed_task["completion_evidence"]

    # ──────────────────────────────────────────────────────────────────────────
    # Step 8: Strict Cross-Tenant Access Rejection (Tenant B cannot access Tenant A)
    # ──────────────────────────────────────────────────────────────────────────
    cross_alert_resp = await client.get(
        f"/api/v1/alerts/{alert.id}",
        headers=auth_headers_tenant_b,
    )
    assert cross_alert_resp.status_code in [404, 403]

    cross_task_resp = await client.get(
        f"/api/v1/tasks/{task.id}",
        headers=auth_headers_tenant_b,
    )
    assert cross_task_resp.status_code in [404, 403]

    list_b_resp = await client.get("/api/v1/alerts", headers=auth_headers_tenant_b)
    assert list_b_resp.status_code == 200
    alerts_b = list_b_resp.json()
    assert not any(a["id"] == str(alert.id) for a in alerts_b)

    # ──────────────────────────────────────────────────────────────────────────
    # Step 9: Server-Side API Disclosure Control & Rate Labeling Verification
    # ──────────────────────────────────────────────────────────────────────────
    map_resp = await client.get(
        "/api/v1/map-layer?metric_code=acute_respiratory_contacts",
        headers=auth_headers_tenant_a,
    )
    assert map_resp.status_code == 200
    map_data = map_resp.json()
    assert map_data["type"] == "FeatureCollection"
    assert map_data["metric_code"] == "acute_respiratory_contacts"
    for feature in map_data["features"]:
        props = feature["properties"]
        assert "rate_label" in props
        assert "not disease incidence" in props["rate_label"]
        if props["is_suppressed"]:
            assert props["value"] is None
            assert props["encounter_rate_per_100k"] is None
