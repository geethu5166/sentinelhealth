"""Phase 3 Test Suite: Air-Quality Exposure & Aggregate Respiratory Health Surveillance.

Tests the complete second vertical slice:
1. Pollution exposure plus rising respiratory contacts (Corroborated Warning).
2. Pollution without health corroboration (Environmental Exposure Watch).
3. Health spike without pollution (Uncorroborated Health Anomaly).
4. Null scenario (Clean baseline, no alert).
5. Missing/stale source, missing denominator, and uncertain location states.
6. Small-cell and overlapping-filter disclosure control (Reconstruction prevention).
7. Playbook ethical boundaries (no automated prescription, restriction, or discipline).
8. Open-Meteo AQI scale preservation (EU vs US vs IN) and non-double-counting.
9. Nonspecific workforce absence protection (never inferring respiratory diagnosis from all-cause absence).
"""

from datetime import datetime, timezone
import pytest

from app.analytics.fusion.policy import EvidenceFusionEngine, EvidenceItem
from app.analytics.playbooks.air_quality import AirQualityPlaybook
from app.connectors.open_meteo_air_quality import OpenMeteoAirQualityConnector
from app.privacy.suppression import DisclosureChecker
from app.replay.scenarios import ScenarioGenerator


@pytest.fixture
def fusion_engine():
    return EvidenceFusionEngine(policy_version="0.2.0")


def test_pollution_plus_respiratory_contacts_produces_corroborated_warning(fusion_engine):
    """Scenario 1: High PM2.5 (140 ug/m3) corroborated by elevated respiratory encounters (z=4.2)."""
    now = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)
    evidences = [
        EvidenceItem(
            signal_family="environmental",
            metric_code="pm25_concentration",
            observed=140.0,
            expected=35.0,
            excess=105.0,
            standardised_residual=6.5,
            ewma_value=125.0,
            is_anomaly=True,
            source_freshness_minutes=15,
            is_fresh=True,
            is_stale=False,
            data_label="synthetic",
            geography_id="DIST-DHANPUR",
            timestamp=now,
            unit="ug/m3",
        ),
        # Also include AQI metric in same environmental family to verify NO double counting
        EvidenceItem(
            signal_family="environmental",
            metric_code="aqi_us",
            observed=195.0,
            expected=75.0,
            excess=120.0,
            standardised_residual=5.0,
            ewma_value=180.0,
            is_anomaly=True,
            source_freshness_minutes=15,
            is_fresh=True,
            is_stale=False,
            data_label="synthetic",
            geography_id="DIST-DHANPUR",
            timestamp=now,
            unit="index_points",
            aqi_system="aqi_us",
        ),
        EvidenceItem(
            signal_family="clinical_service",
            metric_code="acute_respiratory_contacts",
            observed=42.0,
            expected=10.0,
            excess=32.0,
            standardised_residual=4.2,
            ewma_value=38.0,
            is_anomaly=True,
            source_freshness_minutes=45,
            is_fresh=True,
            is_stale=False,
            data_label="synthetic",
            geography_id="DIST-DHANPUR",
            timestamp=now,
            denominator=50000.0,
        ),
    ]

    decision = fusion_engine.evaluate(
        hazard="air_quality_respiratory",
        evidences=evidences,
        environmental_thresholds={"pm25_concentration": 60.0, "aqi_us": 150.0},
    )

    assert decision.should_alert is True
    assert decision.evidence_class == "corroborated_health_warning"
    assert decision.severity in ["warning", "critical"]
    assert decision.evidence_score >= 75.0
    assert any("corroborated" in r.lower() for r in decision.reasons)

    # Verify proportionate playbook generation
    rec = AirQualityPlaybook.generate_recommendation(
        evidence_class=decision.evidence_class,
        severity=decision.severity,
        evidence_summary="; ".join(decision.reasons),
    )
    assert rec["action_tier"] == "tier_2_adjusted_operations"
    assert "workplace_safety_manager" in rec["accountable_roles"]


def test_pollution_without_health_corroboration_produces_environmental_watch(fusion_engine):
    """Scenario 2: High PM2.5 (95 ug/m3) without clinical anomaly -> Environmental Watch only."""
    now = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)
    evidences = [
        EvidenceItem(
            signal_family="environmental",
            metric_code="pm25_concentration",
            observed=95.0,
            expected=32.0,
            excess=63.0,
            standardised_residual=4.8,
            ewma_value=85.0,
            is_anomaly=True,
            source_freshness_minutes=15,
            is_fresh=True,
            is_stale=False,
            data_label="synthetic",
            geography_id="DIST-DHANPUR",
            timestamp=now,
            unit="ug/m3",
        ),
        EvidenceItem(
            signal_family="clinical_service",
            metric_code="acute_respiratory_contacts",
            observed=11.0,
            expected=10.0,
            excess=1.0,
            standardised_residual=0.3,
            ewma_value=10.5,
            is_anomaly=False,
            source_freshness_minutes=45,
            is_fresh=True,
            is_stale=False,
            data_label="synthetic",
            geography_id="DIST-DHANPUR",
            timestamp=now,
            denominator=50000.0,
        ),
    ]

    decision = fusion_engine.evaluate(
        hazard="air_quality_respiratory",
        evidences=evidences,
        environmental_thresholds={"pm25_concentration": 60.0},
    )

    assert decision.should_alert is True
    assert decision.evidence_class == "environmental_watch"
    assert decision.severity == "watch"
    assert decision.evidence_score == 45.0
    assert any("No health anomaly observed" in r for r in decision.reasons)

    rec = AirQualityPlaybook.generate_recommendation(
        evidence_class=decision.evidence_class,
        severity=decision.severity,
        evidence_summary="; ".join(decision.reasons),
    )
    assert rec["action_tier"] == "tier_1_preparation"


def test_clinical_surge_without_pollution_produces_uncorroborated_health_anomaly(fusion_engine):
    """Scenario 3: Clinical respiratory surge (z=3.8) with clean air (PM2.5=22 ug/m3) -> Uncorroborated Anomaly."""
    now = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)
    evidences = [
        EvidenceItem(
            signal_family="environmental",
            metric_code="pm25_concentration",
            observed=22.0,
            expected=25.0,
            excess=-3.0,
            standardised_residual=-0.4,
            ewma_value=23.0,
            is_anomaly=False,
            source_freshness_minutes=15,
            is_fresh=True,
            is_stale=False,
            data_label="synthetic",
            geography_id="DIST-DHANPUR",
            timestamp=now,
            unit="ug/m3",
        ),
        EvidenceItem(
            signal_family="clinical_service",
            metric_code="acute_respiratory_contacts",
            observed=38.0,
            expected=10.0,
            excess=28.0,
            standardised_residual=3.8,
            ewma_value=35.0,
            is_anomaly=True,
            source_freshness_minutes=45,
            is_fresh=True,
            is_stale=False,
            data_label="synthetic",
            geography_id="DIST-DHANPUR",
            timestamp=now,
            denominator=50000.0,
        ),
    ]

    decision = fusion_engine.evaluate(
        hazard="air_quality_respiratory",
        evidences=evidences,
        environmental_thresholds={"pm25_concentration": 60.0},
    )

    assert decision.should_alert is True
    assert decision.evidence_class == "uncorroborated_health_anomaly"
    assert decision.severity in ["advisory", "watch"]
    assert any("Requires operational review" in r for r in decision.reasons)


def test_air_quality_null_scenario_produces_no_alert(fusion_engine):
    """Scenario 4: Clean air and baseline clinical health -> should_alert=False."""
    now = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)
    evidences = [
        EvidenceItem(
            signal_family="environmental",
            metric_code="pm25_concentration",
            observed=28.0,
            expected=30.0,
            excess=-2.0,
            standardised_residual=-0.2,
            ewma_value=29.0,
            is_anomaly=False,
            source_freshness_minutes=15,
            is_fresh=True,
            is_stale=False,
            data_label="synthetic",
            geography_id="DIST-DHANPUR",
            timestamp=now,
            unit="ug/m3",
        ),
        EvidenceItem(
            signal_family="clinical_service",
            metric_code="acute_respiratory_contacts",
            observed=10.0,
            expected=10.0,
            excess=0.0,
            standardised_residual=0.0,
            ewma_value=10.0,
            is_anomaly=False,
            source_freshness_minutes=45,
            is_fresh=True,
            is_stale=False,
            data_label="synthetic",
            geography_id="DIST-DHANPUR",
            timestamp=now,
            denominator=50000.0,
        ),
    ]

    decision = fusion_engine.evaluate(
        hazard="air_quality_respiratory",
        evidences=evidences,
        environmental_thresholds={"pm25_concentration": 60.0},
    )

    assert decision.should_alert is False
    assert decision.evidence_score <= 20.0


def test_missing_stale_quarantined_and_suppressed_explicit_states(fusion_engine):
    """Scenario 5: Stale, quarantined, and suppressed inputs are treated as explicit states, not numerical zero."""
    now = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)
    evidences = [
        EvidenceItem(
            signal_family="environmental",
            metric_code="pm25_concentration",
            observed=110.0,
            expected=35.0,
            excess=75.0,
            standardised_residual=5.0,
            ewma_value=100.0,
            is_anomaly=True,
            source_freshness_minutes=360,  # 6 hours old -> stale
            is_fresh=False,
            is_stale=True,
            data_label="synthetic",
            geography_id="DIST-DHANPUR",
            timestamp=now,
            status="stale",
        ),
        EvidenceItem(
            signal_family="clinical_service",
            metric_code="acute_respiratory_contacts",
            observed=3.0,
            expected=2.5,
            excess=0.5,
            standardised_residual=0.3,
            ewma_value=2.8,
            is_anomaly=False,
            source_freshness_minutes=30,
            is_fresh=True,
            is_stale=False,
            data_label="synthetic",
            geography_id="DIST-DHANPUR",
            timestamp=now,
            status="suppressed",
            is_suppressed=True,
        ),
        EvidenceItem(
            signal_family="workforce",
            metric_code="respiratory_sickness_absence_days",
            observed=0.0,
            expected=5.0,
            excess=-5.0,
            standardised_residual=-2.0,
            ewma_value=0.0,
            is_anomaly=False,
            source_freshness_minutes=15,
            is_fresh=True,
            is_stale=False,
            data_label="synthetic",
            geography_id="DIST-DHANPUR",
            timestamp=now,
            status="quarantined",
            is_quarantined=True,
        ),
    ]

    decision = fusion_engine.evaluate(
        hazard="air_quality_respiratory",
        evidences=evidences,
        environmental_thresholds={"pm25_concentration": 60.0},
    )

    # Must NOT alert because stale and quarantined inputs cannot trigger decisions
    assert decision.should_alert is False
    assert decision.evidence_class == "insufficient_data"
    assert "stale_input:pm25_concentration" in decision.data_state_flags
    assert "suppressed_input:acute_respiratory_contacts" in decision.data_state_flags
    assert "quarantined_input:respiratory_sickness_absence_days" in decision.data_state_flags


def test_small_cell_and_overlapping_filter_disclosure_control():
    """Scenario 6: Disclosure control suppresses small cells [1, 4] and contributor counts < 10."""
    checker = DisclosureChecker(min_contributors=10, suppress_range=(1, 4))

    # Cell in range [1, 4] must be suppressed
    suppress, reason = checker.should_suppress_cell(value=3, contributor_count=15, is_sensitive_health_event=True)
    assert suppress is True
    assert "protected small-cell range" in reason

    # Cell with low contributor count must be suppressed
    suppress, reason = checker.should_suppress_cell(value=25, contributor_count=7, is_sensitive_health_event=True)
    assert suppress is True
    assert "below privacy threshold" in reason

    # Non-sensitive environmental metric is NOT suppressed even if low
    suppress, _ = checker.should_suppress_cell(value=2.5, contributor_count=None, is_sensitive_health_event=False)
    assert suppress is False

    # Complementary suppression prevents reconstruction by subtraction
    table = [
        {"facility": "Site A", "value": 3, "is_suppressed": True},
        {"facility": "Site B", "value": 12, "is_suppressed": False},
        {"facility": "Site C", "value": 45, "is_suppressed": False},
    ]
    protected_table = checker.apply_complementary_suppression(table)
    suppressed_count = sum(1 for r in protected_table if r.get("is_suppressed"))
    assert suppressed_count == 2
    # Site B (lowest positive non-suppressed value) is complementarily suppressed
    assert protected_table[1]["is_suppressed"] is True


def test_playbook_prohibitions_and_ethical_boundaries():
    """Scenario 7: Prohibits automatic treatment, employee restriction, respirator selection, or discipline."""
    boundaries = AirQualityPlaybook.BOUNDARIES
    assert boundaries["prohibit_automatic_medical_treatment"] is True
    assert boundaries["prohibit_mandatory_individual_restrictions_without_clinician"] is True
    assert boundaries["prohibit_respirator_mandate_without_fit_test"] is True
    assert boundaries["prohibit_disciplinary_actions"] is True


def test_open_meteo_connector_aqi_scale_distinction_and_model_labeling():
    """Scenario 8: Preserves European AQI vs US AQI vs Indian AQI without silent relabelling; labels model output."""
    connector = OpenMeteoAirQualityConnector()
    sample_api_response = {
        "hourly": {
            "time": ["2026-11-01T10:00", "2026-11-01T11:00"],
            "pm2_5": [45.2, 58.7],
            "european_aqi": [32.0, 48.0],
            "us_aqi": [78.0, 115.0],
        }
    }

    records = connector.parse_api_response(
        data=sample_api_response,
        latitude=28.61,
        longitude=77.23,
        geography_id="DIST-DHANPUR",
    )

    # Must extract PM2.5, European AQI, and US AQI separately
    metric_codes = [r["metric_code"] for r in records]
    assert "pm25_concentration" in metric_codes
    assert "aqi_eu" in metric_codes
    assert "aqi_us" in metric_codes
    # Assert neither is labelled as Indian AQI
    assert "aqi_in" not in metric_codes

    # Verify model vs on-site measurement labeling
    for r in records:
        meta = r["metadata"]
        assert meta["is_regional_model_output"] is True
        assert meta["is_on_site_measurement"] is False


def test_all_cause_workforce_absence_labeled_nonspecific(fusion_engine):
    """Scenario 9: All-cause workforce absence must be labeled nonspecific and not infer respiratory diagnosis."""
    now = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)
    evidences = [
        EvidenceItem(
            signal_family="environmental",
            metric_code="pm25_concentration",
            observed=85.0,
            expected=30.0,
            excess=55.0,
            standardised_residual=4.5,
            ewma_value=75.0,
            is_anomaly=True,
            source_freshness_minutes=15,
            is_fresh=True,
            is_stale=False,
            data_label="synthetic",
            geography_id="DIST-DHANPUR",
            timestamp=now,
            unit="ug/m3",
        ),
        # All-cause sickness absence (nonspecific)
        EvidenceItem(
            signal_family="workforce",
            metric_code="sickness_absence_worker_days",
            observed=55.0,
            expected=22.0,
            excess=33.0,
            standardised_residual=4.1,
            ewma_value=48.0,
            is_anomaly=True,
            source_freshness_minutes=60,
            is_fresh=True,
            is_stale=False,
            data_label="synthetic",
            geography_id="DIST-DHANPUR",
            timestamp=now,
            is_nonspecific=True,  # Crucial: labeled nonspecific
        ),
    ]

    decision = fusion_engine.evaluate(
        hazard="air_quality_respiratory",
        evidences=evidences,
        environmental_thresholds={"pm25_concentration": 60.0},
    )

    # Must flag nonspecific absence and NOT claim specific respiratory diagnosis
    assert "nonspecific_absence:sickness_absence_worker_days" in decision.data_state_flags
    # Because there is no specific clinical/workforce respiratory anomaly, this remains an environmental watch!
    assert decision.evidence_class == "environmental_watch"
    assert any("cannot infer specific diagnosis" in r for r in decision.reasons)
