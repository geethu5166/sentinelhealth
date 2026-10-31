"""Automated unit tests for CDC-compliant surveillance replay evaluation,
timestamp reconciliations, predefined matching criteria, and timeliness latency metrics.
"""

from datetime import datetime, timedelta, timezone
import pytest
import pandas as pd

from app.replay.runner import (
    simulate_scenario,
    run_comprehensive_replay_suite,
    SCENARIO_GENERATOR_VERSION,
    EVALUATION_GIT_COMMIT,
)
from app.replay.scenarios import ScenarioGenerator


def test_timestamp_latency_reconciliation_gradual_heat():
    """Verify that source-available-to-issue and observation-period-end-to-issue
    latencies match exact timestamp differences without cadence conflation.
    """
    start_date = datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    df, ref = ScenarioGenerator.generate_heat_gradual_scenario(start_date=start_date, days=45, seed=42)

    res = simulate_scenario(
        scenario_name="heat-gradual",
        df=df,
        ref_event=ref,
        policy_name="fused_corroborated",
        start_date=start_date,
        scenario_seed=42,
    )

    perf = res["derived_performance_metrics"]
    timestamps = perf["first_matched_alert_timestamps"]
    assert timestamps is not None

    # Inspect exact timestamps
    t_obs_end = datetime.fromisoformat(timestamps["observation_period_end"])
    t_src_avail = datetime.fromisoformat(timestamps["source_available_at"])
    t_issue = datetime.fromisoformat(timestamps["alert_issued_at"])
    ref_onset = datetime.fromisoformat(ref["onset_at"])
    ref_target = datetime.fromisoformat(ref["earliest_useful_action_at"])

    # 1. Source available -> alert issued: 10 minutes 2 seconds (602 seconds)
    src_to_issue = (t_issue - t_src_avail).total_seconds()
    assert src_to_issue == 602.0
    assert perf["pipeline_latencies"]["source_available_to_issue_seconds"] == 602.0
    assert perf["pipeline_latencies"]["source_available_to_issue_minutes"] == 10.03

    # 2. Observation period end -> alert issued: 15 minutes 3 seconds (903 seconds)
    obs_end_to_issue = (t_issue - t_obs_end).total_seconds()
    assert obs_end_to_issue == 903.0
    assert perf["pipeline_latencies"]["observation_period_end_to_issue_seconds"] == 903.0
    assert perf["pipeline_latencies"]["observation_period_end_to_issue_minutes"] == 15.05

    # 3. Reference onset (July 2, 00:00:00Z) -> actual issue (July 4, 00:15:02Z): ~2 days
    onset_to_issue = (t_issue - ref_onset).total_seconds() / 86400.0
    assert round(onset_to_issue, 2) == 2.01
    assert perf["issue_time_detection_delay_days"] == 2.0104

    # 4. Preparation target (July 1, 00:00:00Z) -> actual issue (July 4, 00:15:02Z): ~3 days late
    target_to_issue_lead = (ref_target - t_issue).total_seconds() / 86400.0
    assert round(target_to_issue_lead, 2) == -3.01
    assert perf["issue_time_useful_lead_days"] == -3.0104

    # 5. Observation-time delay (July 3 observation date vs July 2 onset): 1 day
    assert perf["observation_time_detection_delay_days"] == 1.0
    assert perf["observation_time_useful_lead_days"] == -2.0

    # 6. Provenance metadata labeling
    prov = timestamps["provenance_labels"]
    assert prov["observation_period_end"] == "assumed_daily_cutoff_235959"
    assert prov["source_available_at"] == "assumed_upstream_publication_latency"
    assert prov["alert_issued_at"] == "assumed_notification_dispatch"
    assert prov["scoring_compute_ms"] == "measured_runtime_latency"


def test_predefined_matching_rules_and_early_warning_credit():
    """Verify that alerts within eligible lead window are credited as early warning,
    while alerts outside are reported separately as unmatched false alarms.
    """
    ref_onset = datetime(2026, 7, 2, 0, 0, 0, tzinfo=timezone.utc)
    ref_end = datetime(2026, 7, 9, 0, 0, 0, tzinfo=timezone.utc)
    ref = {
        "event_id": "REF-EVT-HEAT-GRADUAL-2026",
        "hazard": "heat_illness",
        "onset_at": ref_onset.isoformat(),
        "end_at": ref_end.isoformat(),
        "severity": "warning",
        "earliest_useful_action_at": datetime(2026, 7, 1, 0, 0, 0, tzinfo=timezone.utc).isoformat(),
    }

    start_date = datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    df, _ = ScenarioGenerator.generate_heat_gradual_scenario(start_date=start_date, days=45, seed=42)

    res = simulate_scenario(
        scenario_name="heat-gradual",
        df=df,
        ref_event=ref,
        policy_name="fused_corroborated",
        eligible_pre_onset_lead_days=2,
        start_date=start_date,
    )

    reconciliation = res["auditable_episode_reconciliation"]
    # Unmatched episodes before ref_onset - 2 days (Day 20, Day 22) are reported separately
    assert reconciliation["unmatched_alert_episodes"] >= 1

    # Check reason strings for unmatched episodes
    unmatched_eps = [ep for ep in res["episodes"] if not ep["is_matched"]]
    for ep in unmatched_eps:
        assert "Unmatched alert (false alarm)" in ep["matching_reason"]
        assert "exceeding the 2-day eligible lead window" in ep["matching_reason"]


def test_null_scenario_reports_no_reference_event():
    """Verify that a null scenario with no ground-truth reference reports
    'No reference event; one unmatched alert.' without asserting an event was rejected.
    """
    start_date = datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    df, ref = ScenarioGenerator.generate_spurious_health_spike_scenario(start_date=start_date, days=45, seed=202)
    assert ref is None

    res = simulate_scenario(
        scenario_name="spurious-health-spike",
        df=df,
        ref_event=None,
        policy_name="health_only",
        start_date=start_date,
    )

    perf = res["derived_performance_metrics"]
    assert perf["observation_time_detection_delay_days"] is None
    assert perf["issue_time_detection_delay_days"] is None
    assert perf["observation_delay_status"] == "event_missed_or_null"

    # Check that reasons do not claim 'true event rejected'
    for ep in res["episodes"]:
        assert ep["matching_reason"] == "No reference event; one unmatched alert."


def test_provenance_and_version_export():
    """Verify that scenario-generator version, seed, commit, and config are exported."""
    start_date = datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    df, ref = ScenarioGenerator.generate_heat_gradual_scenario(start_date=start_date, days=45, seed=42)

    res = simulate_scenario(
        scenario_name="heat-gradual",
        df=df,
        ref_event=ref,
        policy_name="environmental_only",
        start_date=start_date,
        scenario_seed=42,
    )

    meta = res["scenario_metadata"]
    assert meta["generator_version"] == SCENARIO_GENERATOR_VERSION
    assert meta["seed"] == 42
    assert meta["commit"] == EVALUATION_GIT_COMMIT
    assert meta["configuration"]["temp_threshold_c"] == 39.0
    assert meta["configuration"]["eligible_pre_onset_lead_days"] == 2


def test_exact_timestamp_delay_arithmetic_regression():
    """Regression test ensuring exact mathematical delay calculation from onset and alert_issued_at.

    Directly addresses reporting discrepancies:
    1. July 2, 00:00 -> July 3, 14:00 = 38 hours = +1.5833 days (not +1.01).
    2. November 3, 00:00 -> November 4, 10:00 = 34 hours = +1.4167 days (not +1.04).
    3. July 15, 12:00 -> July 15, 14:00 = 2 hours = +0.0833 days.
    """
    from app.replay.runner import calculate_exact_time_delay

    # Case 1: Heat gradual (July 2, 00:00 -> July 3, 14:00)
    onset_1 = datetime(2026, 7, 2, 0, 0, 0, tzinfo=timezone.utc)
    issue_1 = datetime(2026, 7, 3, 14, 0, 0, tzinfo=timezone.utc)
    res_1 = calculate_exact_time_delay(onset_1, issue_1)
    assert res_1["total_hours"] == 38.0
    assert pytest.approx(res_1["total_days"], 0.001) == 1.5833
    assert res_1["formatted_display"] == "38.0h (+1.58d)"

    # Case 2: Air quality respiratory surge (Nov 3, 00:00 -> Nov 4, 10:00)
    onset_2 = datetime(2026, 11, 3, 0, 0, 0, tzinfo=timezone.utc)
    issue_2 = datetime(2026, 11, 4, 10, 0, 0, tzinfo=timezone.utc)
    res_2 = calculate_exact_time_delay(onset_2, issue_2)
    assert res_2["total_hours"] == 34.0
    assert pytest.approx(res_2["total_days"], 0.001) == 1.4167
    assert res_2["formatted_display"] == "34.0h (+1.42d)"

    # Case 3: Abrupt extreme heat (July 15, 12:00 -> July 15, 14:00)
    onset_3 = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    issue_3 = datetime(2026, 7, 15, 14, 0, 0, tzinfo=timezone.utc)
    res_3 = calculate_exact_time_delay(onset_3, issue_3)
    assert res_3["total_hours"] == 2.0
    assert pytest.approx(res_3["total_days"], 0.001) == 0.0833
    assert res_3["formatted_display"] == "2.0h (+0.08d)"


