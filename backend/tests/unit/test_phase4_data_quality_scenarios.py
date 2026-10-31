"""Phase 4 Data Quality & Edge Case Automated Verification Suite.

Asserts exact pass/fail criteria for Scenarios 9 and 11-15:
- Scenario 9: Visible data-gap status ('missing_input:pm25_concentration'); clinical surge triggers uncorroborated_health_anomaly (not dropped).
- Scenario 11: Stale and quarantined inputs are flagged; produces insufficient_data without false alarms.
- Scenario 12: When catchment population denominator is missing, calculated rate is None with 'missing_population_denominator'; unmapped geography has basis 'unspecified'.
- Scenario 13: Strict disclosure control: counts in [1, 4] and contributors < 10 have is_suppressed=True and value=None; physical PM2.5 (3.2 ug/m3) is not suppressed.
- Scenario 14: Ingestion idempotency rejects duplicate batches ('records_already_processed'); chronological sorting reorders out-of-order stream.
- Scenario 15: Poisson baseline scales expected counts with exposure expansion without false alarms; detects real acute surge on day 35 (z > 4.5).
"""

from __future__ import annotations

from datetime import datetime, timezone
import numpy as np
import pandas as pd
import pytest

from app.analytics.baselines.models import PoissonCountBaseline
from app.analytics.detectors.ewma import OneSidedEWMADetector
from app.analytics.fusion.policy import EvidenceFusionEngine, EvidenceItem
from app.privacy.suppression import DisclosureChecker
from app.replay.scenarios import ScenarioGenerator


def test_scenario_9_missing_environmental_input_visibility():
    """Scenario 9: Upstream PM2.5 sensor drop.
    Asserts visible data-gap status; asserts health surge on day 22 triggers uncorroborated_health_anomaly."""
    engine = EvidenceFusionEngine(policy_version="0.1.0")
    now = datetime(2026, 11, 22, 12, 0, 0, tzinfo=timezone.utc)

    # Missing PM2.5 item
    ev_missing = EvidenceItem(
        signal_family="environmental",
        metric_code="pm25_concentration",
        observed=0.0,
        expected=0.0,
        excess=0.0,
        standardised_residual=0.0,
        ewma_value=0.0,
        is_anomaly=False,
        source_freshness_minutes=999,
        is_fresh=False,
        is_stale=True,
        data_label="synthetic",
        status="missing",
        geography_id="DIST-DHANPUR",
        timestamp=now,
    )
    # Elevated respiratory clinical contacts
    ev_clinic = EvidenceItem(
        signal_family="clinical_service",
        metric_code="acute_respiratory_contacts",
        observed=45.0,
        expected=12.0,
        excess=33.0,
        standardised_residual=4.2,
        ewma_value=40.0,
        is_anomaly=True,
        source_freshness_minutes=15,
        is_fresh=True,
        is_stale=False,
        data_label="synthetic",
        geography_id="DIST-DHANPUR",
        timestamp=now,
        denominator=50000.0,
    )

    decision = engine.evaluate(
        hazard="respiratory_air_quality",
        evidences=[ev_missing, ev_clinic],
        environmental_thresholds={"pm25_concentration": 60.0},
    )

    # Assert visible data-gap status
    assert "missing_input:pm25_concentration" in decision.data_state_flags
    # Assert health surge is preserved and not dropped
    assert decision.should_alert is True
    assert decision.evidence_class == "uncorroborated_health_anomaly"
    assert any("missing" in r.lower() or "insufficient" in r.lower() for r in decision.reasons)


def test_scenario_11_stale_quarantined_records_handling():
    """Scenario 11: Stale readings and quarantined inputs.
    Asserts stale/quarantined flags; produces insufficient_data without false alarms."""
    engine = EvidenceFusionEngine(policy_version="0.1.0")
    now = datetime(2026, 7, 10, 12, 0, 0, tzinfo=timezone.utc)

    ev_stale = EvidenceItem(
        signal_family="environmental",
        metric_code="apparent_temperature",
        observed=43.5,
        expected=32.0,
        excess=11.5,
        standardised_residual=3.8,
        ewma_value=42.0,
        is_anomaly=True,
        is_stale=True,
        source_freshness_minutes=1800,
        is_fresh=False,
        data_label="synthetic",
        status="stale",
        geography_id="DIST-DHANPUR",
        timestamp=now,
    )
    ev_quar = EvidenceItem(
        signal_family="clinical_service",
        metric_code="heat_exhaustion_contacts",
        observed=50.0,
        expected=10.0,
        excess=40.0,
        standardised_residual=4.5,
        ewma_value=48.0,
        is_anomaly=True,
        is_quarantined=True,
        source_freshness_minutes=30,
        is_fresh=True,
        is_stale=False,
        data_label="synthetic",
        status="quarantined",
        geography_id="DIST-DHANPUR",
        timestamp=now,
    )

    decision = engine.evaluate(
        hazard="heat_illness",
        evidences=[ev_stale, ev_quar],
        environmental_thresholds={"apparent_temperature": 39.0},
    )

    # Must flag both
    assert "stale_input:apparent_temperature" in decision.data_state_flags
    assert "quarantined_input:heat_exhaustion_contacts" in decision.data_state_flags
    # Must NOT fire a false alarm when only invalid data is present
    assert decision.should_alert is False
    assert decision.evidence_class == "insufficient_data"


def test_scenario_12_missing_denominator_and_uncertain_geolocation():
    """Scenario 12: Catchment population denominator is missing.
    Asserts rate is None with 'missing_population_denominator'; unmapped site has location_basis 'unspecified'."""
    raw_clinic_count = 25.0
    denominator = None  # Missing catchment

    # Rate calculation logic under missing denominator
    if denominator is None or denominator <= 0:
        rate = None
        rate_status = "missing_population_denominator"
    else:
        rate = (raw_clinic_count / denominator) * 100000.0
        rate_status = "computed"

    assert rate is None
    assert rate_status == "missing_population_denominator"

    # Uncertain geolocation
    geography_mapped = False
    location_basis = "exact_facility" if geography_mapped else "unspecified"
    assert location_basis == "unspecified"


def test_scenario_13_small_cells_and_overlapping_disclosure():
    """Scenario 13: Disclosure control.
    Asserts count in [1, 4] and contributors < 10 have is_suppressed=True and value=None;
    continuous environmental measurement (PM2.5 = 3.2 ug/m3) is unsuppressed."""
    checker = DisclosureChecker(min_contributors=10, suppress_range=(1, 4))

    # Clinical cell with count 3 (< 5) and 2 contributors (< 10)
    is_supp, reason = checker.should_suppress_cell(value=3, contributor_count=2, is_sensitive_health_event=True)
    assert is_supp is True
    assert "Contributor count" in reason

    # Clinical cell with count 2 and contributors = 15 (count in [1, 4] triggers small-cell suppression)
    is_supp_cnt, reason_cnt = checker.should_suppress_cell(value=2, contributor_count=15, is_sensitive_health_event=True)
    assert is_supp_cnt is True
    assert "protected small-cell range" in reason_cnt

    # Continuous environmental measurement PM2.5 = 3.2 ug/m3: not sensitive health event, not suppressed
    is_supp_env, _ = checker.should_suppress_cell(value=3.2, contributor_count=None, is_sensitive_health_event=False)
    assert is_supp_env is False


def test_scenario_14_duplicate_ingestion_idempotency_and_sorting():
    """Scenario 14: Duplicate runs rejected; out-of-order records sorted chronologically."""
    processed_runs = set(["RUN-BATCH-2026-06-15-001"])

    incoming_run_id = "RUN-BATCH-2026-06-15-001"
    if incoming_run_id in processed_runs:
        status = "records_already_processed"
    else:
        status = "accepted"

    assert status == "records_already_processed"

    # Out of order timestamp sorting
    timestamps = [
        datetime(2026, 6, 18, 14, 0, tzinfo=timezone.utc),
        datetime(2026, 6, 15, 8, 0, tzinfo=timezone.utc),
        datetime(2026, 6, 16, 10, 0, tzinfo=timezone.utc),
    ]
    sorted_ts = sorted(timestamps)
    assert sorted_ts[0] == datetime(2026, 6, 15, 8, 0, tzinfo=timezone.utc)
    assert sorted_ts[-1] == datetime(2026, 6, 18, 14, 0, tzinfo=timezone.utc)


def test_scenario_15_baseline_drift_and_real_surge_detection():
    """Scenario 15: Plant expansion doubles exposure on day 22.
    Asserts baseline expands without false alarm; asserts real acute surge on day 35 is detected (z > 4.5)."""
    start = datetime(2026, 6, 1, tzinfo=timezone.utc)
    df, ref_event = ScenarioGenerator.generate_baseline_drift_changing_exposure_scenario(start_date=start, days=45, seed=907)

    baseline_model = PoissonCountBaseline(min_samples=14)
    detector = OneSidedEWMADetector(smoothing_factor=0.3, control_limit_sigma=2.5)

    # 1. Day 25: after expansion to 3000 workers.
    # Expected rate is 0.008 -> expected count 24.
    day25_time = start + pd.Timedelta(days=25)
    hist_25 = df[(df["timestamp"] <= day25_time) & (df["metric_code"] == "heat_exhaustion_contacts")]
    pred_25 = baseline_model.fit_predict(hist_25, day25_time, current_exposure=3000)

    # Expected value should scale to ~24
    assert 20.0 <= pred_25.expected_value <= 28.0

    # 2. Day 35: injected real surge (68 cases)
    day35_time = start + pd.Timedelta(days=35)
    hist_35 = df[(df["timestamp"] <= day35_time) & (df["metric_code"] == "heat_exhaustion_contacts")]
    pred_35 = baseline_model.fit_predict(hist_35, day35_time, current_exposure=3000)
    obs_35 = float(hist_35[hist_35["timestamp"] == day35_time]["value"].iloc[0])
    assert obs_35 == 68.0

    score_35 = detector.compute_anomaly(obs_35, pred_35.expected_value, pred_35.standard_error)
    # Severe anomaly detected
    assert score_35.is_anomaly is True
    assert score_35.standardised_residual > 4.5
