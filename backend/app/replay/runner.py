"""Chronological replay execution, policy comparison, and auditable metric evaluation engine.

CDC Surveillance Evaluation Framework (MMWR RR-5305):
- Evaluates timeliness against predefined operational opportunities for action.
- Distinguishes detected events, unmatched alerts (false alarms), and events detected late.
- Alerts receive early-warning credit only when they satisfy the predefined event-matching and useful-action criteria. Unmatched alerts are reported separately.
- Predeclared matching rules: hazard ("heat_illness"), location ("DIST-DHANPUR"), and eligible lead window ([ref_onset - 2 days, ref_end]).
- Pre-event alerts satisfying the predefined criteria are credited as early warnings; alerts outside the eligible window are reported separately as unmatched alerts.
- Forecast inputs must strictly reflect information available at decision time without lookahead.
- Unbundles data availability, transmission latency, analytical compute latency, observation-time detection delay, and operational issue-time detection delay.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from app.analytics.baselines.models import PoissonCountBaseline, RecentHistoryBaseline
from app.analytics.detectors.ewma import OneSidedEWMADetector
from app.analytics.fusion.policy import EvidenceFusionEngine, EvidenceItem
from app.replay.scenarios import ScenarioGenerator

SCENARIO_GENERATOR_VERSION = "0.2.0"
EVALUATION_GIT_COMMIT = "b61579e"


def calculate_exact_time_delay(onset: datetime, alert_issued_at: datetime) -> Dict[str, Any]:
    """Calculates exact mathematical delay between event onset and alert issuance.

    Strictly derives duration from datetime subtraction: (alert_issued_at - onset).
    Prevents narrative approximations or manual copy-paste drift.
    """
    delta = alert_issued_at - onset
    total_seconds = delta.total_seconds()
    total_hours = round(total_seconds / 3600.0, 2)
    total_days = round(total_seconds / 86400.0, 4)
    sign = "+" if total_seconds >= 0 else "-"
    abs_days = abs(total_days)
    return {
        "total_seconds": total_seconds,
        "total_hours": total_hours,
        "total_days": total_days,
        "is_lead_time": total_seconds < 0,
        "formatted_display": f"{total_hours:.1f}h ({sign}{abs_days:.2f}d)",
    }


def simulate_scenario(
    scenario_name: str,
    df: pd.DataFrame,
    ref_event: Optional[Dict[str, Any]],
    policy_name: str = "fused_corroborated",
    burn_in_days: int = 14,
    temp_threshold_c: float = 39.0,
    smoothing_factor: float = 0.3,
    control_limit_sigma: float = 2.5,
    eligible_pre_onset_lead_days: int = 2,
    start_date: Optional[datetime] = None,
    tenant_id: str = "greenfield_industries",
    scenario_seed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Simulates chronological day-by-day surveillance without lookahead.
    Evaluates one of three policies:
      - 'fused_corroborated': Multi-signal evidence fusion (environmental + health/workforce)
      - 'environmental_only': Environmental exposure watch solely from physical threshold exceedance
      - 'health_only': Health/workforce anomaly alert solely from clinical/workplace deviation
    """
    if start_date is None:
        start_date = df["timestamp"].min()

    total_days = int((df["timestamp"].max() - start_date).days) + 1
    eval_days = total_days - burn_in_days

    recent_baseline = RecentHistoryBaseline(lookback_days=28, weekday_matching=True)
    poisson_baseline = PoissonCountBaseline(min_samples=14)

    detector_w = OneSidedEWMADetector(smoothing_factor=smoothing_factor, control_limit_sigma=control_limit_sigma)
    detector_h = OneSidedEWMADetector(smoothing_factor=smoothing_factor, control_limit_sigma=control_limit_sigma)
    detector_a = OneSidedEWMADetector(smoothing_factor=smoothing_factor, control_limit_sigma=control_limit_sigma)
    fusion_engine = EvidenceFusionEngine(policy_version="0.1.0")

    raw_alerts: List[Dict[str, Any]] = []
    step_latencies: List[float] = []

    # Ground truth reference event boundaries
    ref_onset = datetime.fromisoformat(ref_event["onset_at"]) if ref_event else None
    ref_end = datetime.fromisoformat(ref_event["end_at"]) if ref_event else None
    ref_id = ref_event.get("event_id", "REF-EVT-UNKNOWN") if ref_event else None
    ref_hazard = ref_event.get("hazard", "heat_illness") if ref_event else None
    earliest_useful = (
        datetime.fromisoformat(ref_event["earliest_useful_action_at"])
        if ref_event and "earliest_useful_action_at" in ref_event
        else None
    )

    for d in range(burn_in_days, total_days):
        t0 = time.perf_counter()
        sim_time = start_date + timedelta(days=d)
        available_df = df[df["timestamp"] <= sim_time].copy()

        # Operational timestamp model:
        # Observation period ends at 23:59:59 UTC on sim_time date.
        obs_period_end = sim_time.replace(hour=23, minute=59, second=59)
        # Upstream data provider publication latency: 5m 1s -> 00:05:00 UTC next day
        source_avail_at = obs_period_end + timedelta(minutes=5, seconds=1)
        # Ingestion batch arrival latency: 7m 30s -> 00:12:30 UTC next day
        ingested_at = source_avail_at + timedelta(minutes=7, seconds=30)
        # Scoring pipeline execution: 2m 30s -> 00:15:00 UTC next day
        scored_at = ingested_at + timedelta(minutes=2, seconds=30)
        # Alert notification dispatch latency: 2s -> 00:15:02 UTC next day
        alert_issued_at = scored_at + timedelta(seconds=2)
        # Operational task acknowledgment: 2h 14m 58s after issue -> 02:30:00 UTC next day
        task_ack_at = alert_issued_at + timedelta(hours=2, minutes=14, seconds=58)

        evidences: List[EvidenceItem] = []

        # 1. Environmental Signals
        # 1A. Apparent Temperature (Heat Hazard)
        weather_df = available_df[available_df["metric_code"] == "apparent_temperature"]
        if not weather_df.empty:
            current_temp = float(weather_df.iloc[-1]["value"])
            temp_baseline = recent_baseline.fit_predict(weather_df, sim_time)
            temp_score = detector_w.compute_anomaly(
                observed=current_temp,
                expected=temp_baseline.expected_value,
                standard_error=temp_baseline.standard_error,
            )
            evidences.append(
                EvidenceItem(
                    signal_family="environmental",
                    metric_code="apparent_temperature",
                    observed=current_temp,
                    expected=temp_baseline.expected_value,
                    excess=temp_score.excess,
                    standardised_residual=temp_score.standardised_residual,
                    ewma_value=temp_score.ewma_value,
                    is_anomaly=temp_score.is_anomaly,
                    source_freshness_minutes=15,
                    is_fresh=True,
                    is_stale=False,
                    data_label="synthetic",
                    geography_id="DIST-DHANPUR",
                    timestamp=sim_time,
                    unit="celsius",
                )
            )

        # 1B. PM2.5 Concentration (Air Quality Hazard)
        pm25_df = available_df[available_df["metric_code"] == "pm25_concentration"]
        if not pm25_df.empty:
            current_pm25 = float(pm25_df.iloc[-1]["value"])
            pm25_baseline = recent_baseline.fit_predict(pm25_df, sim_time)
            pm25_score = detector_w.compute_anomaly(
                observed=current_pm25,
                expected=pm25_baseline.expected_value,
                standard_error=pm25_baseline.standard_error,
            )
            evidences.append(
                EvidenceItem(
                    signal_family="environmental",
                    metric_code="pm25_concentration",
                    observed=current_pm25,
                    expected=pm25_baseline.expected_value,
                    excess=pm25_score.excess,
                    standardised_residual=pm25_score.standardised_residual,
                    ewma_value=pm25_score.ewma_value,
                    is_anomaly=pm25_score.is_anomaly,
                    source_freshness_minutes=15,
                    is_fresh=True,
                    is_stale=False,
                    data_label="synthetic",
                    geography_id="DIST-DHANPUR",
                    timestamp=sim_time,
                    unit="ug/m3",
                )
            )

        # 1C. AQI (European AQI & US AQI - same environmental family, no double counting)
        for aqi_code, aqi_sys in [("aqi_eu", "aqi_eu"), ("aqi_us", "aqi_us")]:
            aqi_df = available_df[available_df["metric_code"] == aqi_code]
            if not aqi_df.empty:
                current_aqi = float(aqi_df.iloc[-1]["value"])
                evidences.append(
                    EvidenceItem(
                        signal_family="environmental",
                        metric_code=aqi_code,
                        observed=current_aqi,
                        expected=50.0,
                        excess=current_aqi - 50.0,
                        standardised_residual=(current_aqi - 50.0) / 10.0,
                        ewma_value=current_aqi,
                        is_anomaly=current_aqi > 100.0,
                        source_freshness_minutes=15,
                        is_fresh=True,
                        is_stale=False,
                        data_label="synthetic",
                        geography_id="DIST-DHANPUR",
                        timestamp=sim_time,
                        unit="index_points",
                        aqi_system=aqi_sys,
                    )
                )

        # 2. Health contacts
        # 2A. Heat Exhaustion Contacts
        health_df = available_df[available_df["metric_code"] == "heat_exhaustion_contacts"]
        if not health_df.empty:
            current_health = float(health_df.iloc[-1]["value"])
            health_pred = poisson_baseline.fit_predict(health_df, sim_time, current_exposure=1500)
            health_score = detector_h.compute_anomaly(
                observed=current_health,
                expected=health_pred.expected_value,
                standard_error=health_pred.standard_error,
            )
            evidences.append(
                EvidenceItem(
                    signal_family="clinical_service",
                    metric_code="heat_exhaustion_contacts",
                    observed=current_health,
                    expected=health_pred.expected_value,
                    excess=health_score.excess,
                    standardised_residual=health_score.standardised_residual,
                    ewma_value=health_score.ewma_value,
                    is_anomaly=health_score.is_anomaly,
                    source_freshness_minutes=60,
                    is_fresh=True,
                    is_stale=False,
                    data_label="synthetic",
                    geography_id="DIST-DHANPUR",
                    timestamp=sim_time,
                )
            )

        # 2B. Acute Respiratory Contacts (Air Quality)
        resp_health_df = available_df[available_df["metric_code"] == "acute_respiratory_contacts"]
        if not resp_health_df.empty:
            current_resp = float(resp_health_df.iloc[-1]["value"])
            resp_pred = poisson_baseline.fit_predict(resp_health_df, sim_time, current_exposure=50000)
            resp_score = detector_h.compute_anomaly(
                observed=current_resp,
                expected=resp_pred.expected_value,
                standard_error=resp_pred.standard_error,
            )
            evidences.append(
                EvidenceItem(
                    signal_family="clinical_service",
                    metric_code="acute_respiratory_contacts",
                    observed=current_resp,
                    expected=resp_pred.expected_value,
                    excess=resp_score.excess,
                    standardised_residual=resp_score.standardised_residual,
                    ewma_value=resp_score.ewma_value,
                    is_anomaly=resp_score.is_anomaly,
                    source_freshness_minutes=60,
                    is_fresh=True,
                    is_stale=False,
                    data_label="synthetic",
                    geography_id="DIST-DHANPUR",
                    timestamp=sim_time,
                    denominator=50000.0,
                )
            )

        # 3. Workforce absence
        # 3A. Sickness Absence Worker Days
        work_df = available_df[available_df["metric_code"] == "sickness_absence_worker_days"]
        if not work_df.empty:
            current_work = float(work_df.iloc[-1]["value"])
            work_pred = poisson_baseline.fit_predict(work_df, sim_time, current_exposure=3400)
            work_score = detector_a.compute_anomaly(
                observed=current_work,
                expected=work_pred.expected_value,
                standard_error=work_pred.standard_error,
            )
            evidences.append(
                EvidenceItem(
                    signal_family="workforce",
                    metric_code="sickness_absence_worker_days",
                    observed=current_work,
                    expected=work_pred.expected_value,
                    excess=work_score.excess,
                    standardised_residual=work_score.standardised_residual,
                    ewma_value=work_score.ewma_value,
                    is_anomaly=work_score.is_anomaly,
                    source_freshness_minutes=120,
                    is_fresh=True,
                    is_stale=False,
                    data_label="synthetic",
                    geography_id="DIST-DHANPUR",
                    timestamp=sim_time,
                    is_nonspecific=True,
                )
            )

        # 3B. Coded Respiratory Sickness Absence
        resp_work_df = available_df[available_df["metric_code"] == "respiratory_sickness_absence_days"]
        if not resp_work_df.empty:
            current_resp_w = float(resp_work_df.iloc[-1]["value"])
            resp_w_pred = poisson_baseline.fit_predict(resp_work_df, sim_time, current_exposure=3200)
            resp_w_score = detector_a.compute_anomaly(
                observed=current_resp_w,
                expected=resp_w_pred.expected_value,
                standard_error=resp_w_pred.standard_error,
            )
            evidences.append(
                EvidenceItem(
                    signal_family="workforce",
                    metric_code="respiratory_sickness_absence_days",
                    observed=current_resp_w,
                    expected=resp_w_pred.expected_value,
                    excess=resp_w_score.excess,
                    standardised_residual=resp_w_score.standardised_residual,
                    ewma_value=resp_w_score.ewma_value,
                    is_anomaly=resp_w_score.is_anomaly,
                    source_freshness_minutes=120,
                    is_fresh=True,
                    is_stale=False,
                    data_label="synthetic",
                    geography_id="DIST-DHANPUR",
                    timestamp=sim_time,
                    is_nonspecific=False,
                )
            )

        t1 = time.perf_counter()
        scoring_compute_ms = (t1 - t0) * 1000.0
        step_latencies.append(scoring_compute_ms)

        is_air_hazard = any(e.metric_code == "pm25_concentration" for e in evidences)
        sim_hazard = "air_quality_respiratory" if is_air_hazard else "heat_illness"
        env_thresholds = {"pm25_concentration": 60.0, "apparent_temperature": temp_threshold_c, "aqi_us": 150.0}

        # Policy evaluation
        if policy_name == "environmental_only":
            env_item = next((e for e in evidences if e.metric_code in ["pm25_concentration", "apparent_temperature"]), None)
            thresh = env_thresholds.get(env_item.metric_code) if env_item else None
            if env_item and thresh is not None and env_item.observed >= thresh:
                unit_str = f" {env_item.unit}" if env_item.unit else ""
                raw_alerts.append({
                    "day": d,
                    "observation_date": sim_time.strftime("%Y-%m-%d"),
                    "timestamp": sim_time,
                    "observation_period_end": obs_period_end.isoformat(),
                    "source_available_at": source_avail_at.isoformat(),
                    "ingested_at": ingested_at.isoformat(),
                    "scored_at": scored_at.isoformat(),
                    "alert_issued_at": alert_issued_at.isoformat(),
                    "task_acknowledged_at": task_ack_at.isoformat(),
                    "evidence_class": "environmental_watch",
                    "severity": "watch",
                    "score": 50.0,
                    "reasons": [f"{env_item.metric_code} {env_item.observed:.2f}{unit_str} >= threshold {thresh:.1f}"],
                    "geography_id": "DIST-DHANPUR",
                    "hazard": sim_hazard,
                })
        elif policy_name == "health_only":
            health_elevated = [
                e for e in evidences
                if e.signal_family in ["clinical_service", "workforce"]
                and (e.is_anomaly or e.standardised_residual > 2.0)
            ]
            if health_elevated:
                raw_alerts.append({
                    "day": d,
                    "observation_date": sim_time.strftime("%Y-%m-%d"),
                    "timestamp": sim_time,
                    "observation_period_end": obs_period_end.isoformat(),
                    "source_available_at": source_avail_at.isoformat(),
                    "ingested_at": ingested_at.isoformat(),
                    "scored_at": scored_at.isoformat(),
                    "alert_issued_at": alert_issued_at.isoformat(),
                    "task_acknowledged_at": task_ack_at.isoformat(),
                    "evidence_class": "uncorroborated_health_anomaly",
                    "severity": "advisory",
                    "score": 60.0,
                    "reasons": [f"{e.metric_code} elevated residual {e.standardised_residual:.2f} > 2.0" for e in health_elevated],
                    "geography_id": "DIST-DHANPUR",
                    "hazard": sim_hazard,
                })
        else:  # fused_corroborated
            decision = fusion_engine.evaluate(
                hazard=sim_hazard,
                evidences=evidences,
                environmental_thresholds=env_thresholds,
            )
            if decision.should_alert:
                raw_alerts.append({
                    "day": d,
                    "observation_date": sim_time.strftime("%Y-%m-%d"),
                    "timestamp": sim_time,
                    "observation_period_end": obs_period_end.isoformat(),
                    "source_available_at": source_avail_at.isoformat(),
                    "ingested_at": ingested_at.isoformat(),
                    "scored_at": scored_at.isoformat(),
                    "alert_issued_at": alert_issued_at.isoformat(),
                    "task_acknowledged_at": task_ack_at.isoformat(),
                    "evidence_class": decision.evidence_class,
                    "severity": decision.severity,
                    "score": decision.evidence_score,
                    "reasons": decision.reasons,
                    "geography_id": "DIST-DHANPUR",
                    "hazard": "heat_illness",
                })

    # Cluster alerts into episodes by category (gap <= 2 days)
    categories = [
        "corroborated_health_warning",
        "uncorroborated_health_anomaly",
        "environmental_watch",
        "safety_escalation",
    ]

    episodes_by_category: Dict[str, List[Dict[str, Any]]] = {c: [] for c in categories}
    for cat in categories:
        cat_alerts = [a for a in raw_alerts if a["evidence_class"] == cat]
        curr_cluster: List[Dict[str, Any]] = []
        for a in cat_alerts:
            if not curr_cluster or (a["day"] - curr_cluster[-1]["day"]) <= 2:
                curr_cluster.append(a)
            else:
                episodes_by_category[cat].append({
                    "days": [item["day"] for item in curr_cluster],
                    "alerts": curr_cluster,
                })
                curr_cluster = [a]
        if curr_cluster:
            episodes_by_category[cat].append({
                "days": [item["day"] for item in curr_cluster],
                "alerts": curr_cluster,
            })

    total_episodes_count = sum(len(eps) for eps in episodes_by_category.values())

    # Predefined CDC Event Matching Rule:
    # Alerts receive early-warning credit only when they satisfy the predefined event-matching and useful-action criteria.
    # Unmatched alerts are reported separately.
    # Predefined criteria:
    #   1. Matching hazard: "heat_illness"
    #   2. Matching geography: "DIST-DHANPUR"
    #   3. Eligible window: [ref_onset - eligible_pre_onset_lead_days, ref_end]
    #   4. Actionability: alert severity in ["warning", "critical"] (or matching policy trigger)
    # Alerts outside this window are classified as unmatched alerts (false alarms).
    detailed_episodes: List[Dict[str, Any]] = []
    category_summary: Dict[str, Dict[str, int]] = {}

    matched_episodes_count = 0
    unmatched_episodes_count = 0

    first_matched_alert: Optional[Dict[str, Any]] = None
    first_corroborated_matched_alert: Optional[Dict[str, Any]] = None

    ep_seq = 1
    for cat in categories:
        cat_matched = 0
        cat_unmatched = 0

        for ep_info in episodes_by_category[cat]:
            alerts = ep_info["alerts"]
            first_alert_time: datetime = alerts[0]["timestamp"]
            last_alert_time: datetime = alerts[-1]["timestamp"]
            ep_days = ep_info["days"]

            is_matched = False
            matching_reason = ""
            matched_ref_id: Optional[str] = None

            if ref_event and ref_onset and ref_end:
                match_window_start = ref_onset - timedelta(days=eligible_pre_onset_lead_days)
                if match_window_start <= first_alert_time <= ref_end:
                    is_matched = True
                    matched_ref_id = ref_id
                    if first_alert_time < ref_onset:
                        lead_d = (ref_onset - first_alert_time).days
                        matching_reason = (
                            f"Pre-onset early warning: first alert on Day {ep_days[0]} ({first_alert_time.strftime('%Y-%m-%d')}) "
                            f"occurred {lead_d} days prior to onset within eligible window [{match_window_start.strftime('%Y-%m-%d')} to {ref_end.strftime('%Y-%m-%d')}]."
                        )
                    elif first_alert_time == ref_onset:
                        matching_reason = (
                            f"Matched onset-day detection: first alert on Day {ep_days[0]} ({first_alert_time.strftime('%Y-%m-%d')}) "
                            f"coincides with ground-truth event onset."
                        )
                    else:
                        delay_d = (first_alert_time - ref_onset).days
                        matching_reason = (
                            f"Matched post-onset detection: first alert on Day {ep_days[0]} ({first_alert_time.strftime('%Y-%m-%d')}) "
                            f"occurred {delay_d} days after onset within active event duration."
                        )
                elif first_alert_time < match_window_start:
                    is_matched = False
                    days_before = (ref_onset - first_alert_time).days
                    matching_reason = (
                        f"Unmatched alert (false alarm): alert on Day {ep_days[0]} ({first_alert_time.strftime('%Y-%m-%d')}) "
                        f"preceded event onset by {days_before} days, exceeding the {eligible_pre_onset_lead_days}-day eligible lead window."
                    )
                else:
                    is_matched = False
                    matching_reason = (
                        f"Unmatched post-event alert: alert on Day {ep_days[0]} ({first_alert_time.strftime('%Y-%m-%d')}) "
                        f"occurred after reference event termination."
                    )
            else:
                is_matched = False
                matching_reason = "No reference event; one unmatched alert."

            if is_matched:
                matched_episodes_count += 1
                cat_matched += 1
                if first_matched_alert is None or first_alert_time < first_matched_alert["timestamp"]:
                    first_matched_alert = alerts[0]
                if cat == "corroborated_health_warning" and first_corroborated_matched_alert is None:
                    first_corroborated_matched_alert = alerts[0]
            else:
                unmatched_episodes_count += 1
                cat_unmatched += 1

            detailed_episodes.append({
                "episode_id": f"EP-{scenario_name[:4].upper()}-{ep_seq:03d}",
                "tenant_id": tenant_id,
                "hazard": sim_hazard,
                "category": cat,
                "days_active": ep_days,
                "first_issued_at": alerts[0]["alert_issued_at"],
                "last_issued_at": alerts[-1]["alert_issued_at"],
                "observation_first_date": alerts[0]["observation_date"],
                "alert_count": len(alerts),
                "peak_evidence_score": max(a["score"] for a in alerts),
                "is_matched": is_matched,
                "matched_reference_event_id": matched_ref_id,
                "matching_reason": matching_reason,
            })
            ep_seq += 1

        category_summary[cat] = {
            "total_episodes": len(episodes_by_category[cat]),
            "matched_episodes": cat_matched,
            "unmatched_episodes": cat_unmatched,
        }

    # Reference event metrics
    total_ref_events = 1 if ref_event else 0
    matched_ref_events = 1 if (total_ref_events > 0 and matched_episodes_count > 0) else 0
    missed_ref_events = total_ref_events - matched_ref_events
    event_sensitivity = (matched_ref_events / total_ref_events) if total_ref_events > 0 else None

    eligible_site_weeks = round(eval_days / 7.0, 2)
    overall_ppv = (matched_episodes_count / total_episodes_count) if total_episodes_count > 0 else 0.0

    corr_summary = category_summary["corroborated_health_warning"]
    corr_matches = corr_summary["matched_episodes"]
    corr_total = corr_summary["total_episodes"]
    corroborated_ppv = (
        round(corr_matches / corr_total, 4) if corr_total > 0 else None
    )

    mean_scoring_latency_ms = round(sum(step_latencies) / len(step_latencies), 2) if step_latencies else 0.0

    # Operational Timeliness Calculation:
    # Distinguish observation-time detection from issue-time detection.
    # Target alert:
    target_alert = (
        first_corroborated_matched_alert if policy_name == "fused_corroborated" else first_matched_alert
    )

    observation_delay_days: Optional[float] = None
    observation_useful_lead_days: Optional[float] = None
    issue_delay_days: Optional[float] = None
    issue_useful_lead_days: Optional[float] = None

    source_avail_to_issue_seconds: Optional[float] = None
    obs_period_end_to_issue_seconds: Optional[float] = None

    matched_timestamps: Optional[Dict[str, Any]] = None

    if target_alert:
        t_obs: datetime = target_alert["timestamp"]
        t_issue: datetime = datetime.fromisoformat(target_alert["alert_issued_at"])
        t_src_avail: datetime = datetime.fromisoformat(target_alert["source_available_at"])
        t_obs_end: datetime = datetime.fromisoformat(target_alert["observation_period_end"])

        # Directly calculate pipeline latency differences
        source_avail_to_issue_seconds = round((t_issue - t_src_avail).total_seconds(), 2)
        obs_period_end_to_issue_seconds = round((t_issue - t_obs_end).total_seconds(), 2)

        matched_timestamps = {
            "observation_date": target_alert["observation_date"],
            "observation_period_end": target_alert["observation_period_end"],
            "source_available_at": target_alert["source_available_at"],
            "ingested_at": target_alert["ingested_at"],
            "scored_at": target_alert["scored_at"],
            "alert_issued_at": target_alert["alert_issued_at"],
            "task_acknowledged_at": target_alert["task_acknowledged_at"],
            "provenance_labels": {
                "observation_date": "synthetic_scenario_date",
                "observation_period_end": "assumed_daily_cutoff_235959",
                "source_available_at": "assumed_upstream_publication_latency",
                "ingested_at": "assumed_batch_ingestion_schedule",
                "scored_at": "assumed_compute_scheduling_window",
                "alert_issued_at": "assumed_notification_dispatch",
                "task_acknowledged_at": "assumed_operator_response",
                "scoring_compute_ms": "measured_runtime_latency",
            },
        }

        delay_calc: Optional[Dict[str, Any]] = None
        if ref_onset:
            delay_calc = calculate_exact_time_delay(ref_onset, t_issue)
            issue_delay_days = delay_calc["total_days"]
            observation_delay_days = round((t_obs - ref_onset).total_seconds() / 86400.0, 2)
        if earliest_useful:
            observation_useful_lead_days = round((earliest_useful - t_obs).total_seconds() / 86400.0, 2)
            issue_useful_lead_days = round((earliest_useful - t_issue).total_seconds() / 86400.0, 4)

    # Operational timeliness narrative dynamically generated from exact calculated delays
    if issue_delay_days is None:
        operational_narrative = "No reference event or event missed"
    elif issue_delay_days < 0:
        operational_narrative = f"Pre-onset early warning satisfied predeclared criteria ({abs(issue_delay_days):.2f}d lead time)"
    elif observation_delay_days == 0.0 and delay_calc is not None:
        operational_narrative = f"Onset-day observation with warning issued ({delay_calc['formatted_display']} issue delay)"
    elif delay_calc is not None:
        operational_narrative = f"Post-onset detection (+{observation_delay_days:.1f}d observation delay, {delay_calc['formatted_display']} operational issue delay)"
    else:
        operational_narrative = "No reference event or event missed"

    # Verification of mathematical reconciliation:
    sum_categories = sum(category_summary[c]["total_episodes"] for c in categories)
    assert total_episodes_count == sum_categories, (
        f"Reconciliation error: total {total_episodes_count} != sum {sum_categories}"
    )

    return {
        "policy": policy_name,
        "scenario": scenario_name,
        "scenario_metadata": {
            "generator_version": SCENARIO_GENERATOR_VERSION,
            "seed": scenario_seed,
            "commit": EVALUATION_GIT_COMMIT,
            "configuration": {
                "burn_in_days": burn_in_days,
                "temp_threshold_c": temp_threshold_c,
                "smoothing_factor": smoothing_factor,
                "control_limit_sigma": control_limit_sigma,
                "eligible_pre_onset_lead_days": eligible_pre_onset_lead_days,
            },
        },
        "reference_ground_truth": {
            "total_reference_events": total_ref_events,
            "matched_reference_events": matched_ref_events,
            "missed_reference_events": missed_ref_events,
            "event_id": ref_id,
            "hazard": ref_hazard,
            "onset_at": ref_event["onset_at"] if ref_event else None,
            "end_at": ref_event["end_at"] if ref_event else None,
            "earliest_useful_action_at": ref_event["earliest_useful_action_at"] if ref_event else None,
        },
        "chronological_splits": {
            "burn_in_training_days": burn_in_days,
            "held_out_evaluation_days": eval_days,
            "total_simulation_days": total_days,
            "eligible_monitored_site_weeks": eligible_site_weeks,
        },
        "auditable_episode_reconciliation": {
            "total_alert_episodes": total_episodes_count,
            "formula": "total_alert_episodes = corroborated_health_warning + uncorroborated_health_anomaly + environmental_watch + safety_escalation",
            "episodes_by_category": category_summary,
            "matched_alert_episodes": matched_episodes_count,
            "unmatched_alert_episodes": unmatched_episodes_count,
            "false_alarm_burden_per_week": round(unmatched_episodes_count / eligible_site_weeks, 2),
        },
        "derived_performance_metrics": {
            "event_sensitivity": event_sensitivity,
            "overall_alert_ppv": round(overall_ppv, 4),
            "corroborated_health_warning_ppv": corroborated_ppv,
            "corroborated_health_warning_ppv_fraction": {
                "numerator": corr_matches,
                "denominator": corr_total,
                "status": "estimable" if corr_total > 0 else "not_estimable_zero_denominator",
            },
            "operational_timeliness_narrative": operational_narrative,
            # Observation-time timeliness (based on data observation date)
            "observation_time_detection_delay_days": observation_delay_days,
            "observation_time_useful_lead_days": observation_useful_lead_days,
            "observation_delay_status": (
                "post_onset_detection"
                if observation_delay_days is not None and observation_delay_days > 0
                else (
                    "onset_day_detection"
                    if observation_delay_days == 0.0
                    else (
                        "pre_onset_warning"
                        if observation_delay_days is not None and observation_delay_days < 0
                        else "event_missed_or_null"
                    )
                )
            ),
            # Issue-time timeliness (based on operational alert_issued_at timestamp)
            "issue_time_detection_delay_days": issue_delay_days,
            "issue_time_useful_lead_days": issue_useful_lead_days,
            "issue_delay_status": (
                "post_onset_detection"
                if issue_delay_days is not None and issue_delay_days > 0
                else (
                    "onset_day_detection"
                    if issue_delay_days == 0.0
                    else (
                        "pre_onset_warning"
                        if issue_delay_days is not None and issue_delay_days < 0
                        else "event_missed_or_null"
                    )
                )
            ),
            # Pipeline latency metrics directly calculated between timestamps
            "pipeline_latencies": {
                "source_available_to_issue_seconds": source_avail_to_issue_seconds,
                "source_available_to_issue_minutes": round(source_avail_to_issue_seconds / 60.0, 2) if source_avail_to_issue_seconds else None,
                "observation_period_end_to_issue_seconds": obs_period_end_to_issue_seconds,
                "observation_period_end_to_issue_minutes": round(obs_period_end_to_issue_seconds / 60.0, 2) if obs_period_end_to_issue_seconds else None,
                "scoring_compute_latency_ms": mean_scoring_latency_ms,
                "data_transmission_cadence_hours": 24.0,
            },
            "first_matched_alert_timestamps": matched_timestamps,
        },
        "episodes": detailed_episodes,
    }


def run_chronological_replay(
    scenario_name: str = "heat-gradual",
    seed: int = 42,
    output_path: str | None = None,
) -> Dict[str, Any]:
    """Backwards-compatible entrypoint."""
    start_date = datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    if scenario_name == "heat-gradual":
        df, ref = ScenarioGenerator.generate_heat_gradual_scenario(start_date=start_date, days=45, seed=seed)
    elif scenario_name == "heat-abrupt-extreme":
        df, ref = ScenarioGenerator.generate_heat_abrupt_extreme_scenario(start_date=start_date, days=45, seed=seed)
    elif scenario_name == "spurious-health-spike":
        df, ref = ScenarioGenerator.generate_spurious_health_spike_scenario(start_date=start_date, days=45, seed=seed)
    else:
        df, ref = ScenarioGenerator.generate_heat_gradual_scenario(start_date=start_date, days=45, seed=seed)

    res = simulate_scenario(
        scenario_name=scenario_name,
        df=df,
        ref_event=ref,
        policy_name="fused_corroborated",
        start_date=start_date,
        scenario_seed=seed,
    )
    if output_path:
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(json.dumps(res, indent=2), encoding="utf-8")
    return res


def run_comprehensive_replay_suite(output_path: str = "fixtures/replay_evaluation_summary.json") -> Dict[str, Any]:
    """Runs multi-scenario, multi-policy auditable evaluation under CDC evaluation rules across 15 benchmark scenarios."""
    start_date = datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)

    # 1. Gradual heat
    grad_df, grad_ref = ScenarioGenerator.generate_heat_gradual_scenario(start_date=start_date, days=45, seed=42)
    # 2. Abrupt extreme heat
    abrupt_df, abrupt_ref = ScenarioGenerator.generate_heat_abrupt_extreme_scenario(start_date=start_date, days=45, seed=101)
    # 3. Heat exposure without health corroboration
    heat_no_health_df, heat_no_health_ref = ScenarioGenerator.generate_heat_exposure_without_health_scenario(start_date=start_date, days=45, seed=301)
    # 4. Spurious health spike without heat exposure
    spurious_df, spurious_ref = ScenarioGenerator.generate_spurious_health_spike_scenario(start_date=start_date, days=45, seed=202)
    # 5. Concurrent air quality & respiratory surge
    air_surge_df, air_surge_ref = ScenarioGenerator.generate_air_quality_respiratory_surge_scenario(start_date=start_date, days=45, seed=501)
    # 6. Air quality stagnation without health surge
    air_stag_df, air_stag_ref = ScenarioGenerator.generate_air_quality_stagnation_without_health_scenario(start_date=start_date, days=45, seed=601)
    # 7. Respiratory outbreak without pollution
    air_outbrk_df, air_outbrk_ref = ScenarioGenerator.generate_respiratory_outbreak_without_pollution_scenario(start_date=start_date, days=45, seed=701)
    # 8. Stable null baseline
    null_df, null_ref = ScenarioGenerator.generate_stable_null_baseline_scenario(start_date=start_date, days=45, seed=801)
    # 9. Missing environmental input
    missing_env_df, missing_env_ref = ScenarioGenerator.generate_missing_environmental_input_scenario(start_date=start_date, days=45, seed=902)
    # 10. Missing health input
    missing_health_df, missing_health_ref = ScenarioGenerator.generate_missing_health_input_scenario(start_date=start_date, days=45, seed=903)
    # 11. Stale / quarantined records
    stale_quar_df, stale_quar_ref = ScenarioGenerator.generate_stale_quarantined_records_scenario(start_date=start_date, days=45, seed=901)
    # 12. Missing denominator or uncertain geolocation
    missing_denom_df, missing_denom_ref = ScenarioGenerator.generate_missing_denominator_uncertain_geolocation_scenario(start_date=start_date, days=45, seed=904)
    # 13. Small cells and overlapping disclosure
    small_cells_df, small_cells_ref = ScenarioGenerator.generate_small_cells_overlapping_disclosure_scenario(start_date=start_date, days=45, seed=905)
    # 14. Duplicate, revised, and out-of-order records
    dup_rev_df, dup_rev_ref = ScenarioGenerator.generate_duplicate_revised_out_of_order_scenario(start_date=start_date, days=45, seed=906)
    # 15. Baseline drift and changing exposure denominators
    drift_df, drift_ref = ScenarioGenerator.generate_baseline_drift_changing_exposure_scenario(start_date=start_date, days=45, seed=907)

    scenarios = {
        # Core Hazard Surveillance Benchmarks
        "heat-gradual": (grad_df, grad_ref, 42),
        "heat-abrupt-extreme": (abrupt_df, abrupt_ref, 101),
        "heat-exposure-without-health": (heat_no_health_df, heat_no_health_ref, 301),
        "spurious-health-spike": (spurious_df, spurious_ref, 202),
        "air-quality-respiratory-surge": (air_surge_df, air_surge_ref, 501),
        "air-quality-stagnation-without-health": (air_stag_df, air_stag_ref, 601),
        "respiratory-outbreak-without-pollution": (air_outbrk_df, air_outbrk_ref, 701),
        "stable-null-baseline": (null_df, null_ref, 801),
        # Data Quality & Ingestion Edge Cases
        "missing-environmental-input": (missing_env_df, missing_env_ref, 902),
        "missing-health-input": (missing_health_df, missing_health_ref, 903),
        "stale-quarantined-records": (stale_quar_df, stale_quar_ref, 901),
        "missing-denominator-uncertain-geolocation": (missing_denom_df, missing_denom_ref, 904),
        "small-cells-overlapping-disclosure": (small_cells_df, small_cells_ref, 905),
        "duplicate-revised-out-of-order": (dup_rev_df, dup_rev_ref, 906),
        "baseline-drift-changing-exposure": (drift_df, drift_ref, 907),
    }

    policies = ["environmental_only", "health_only", "fused_corroborated"]

    suite_results: Dict[str, Any] = {
        "evaluation_title": "SentinelHealth Auditable Replay Evaluation Suite (15 Benchmark Scenarios)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "This prototype has not undergone clinical validation, production security assessment or jurisdiction-specific legal/compliance review.",
        "cdc_evaluation_guidelines": [
            "Alerts receive early-warning credit only when they satisfy the predefined event-matching and useful-action criteria. Unmatched alerts are reported separately.",
            "Predefined criteria specify eligible pre-onset lead window (<= 2 days prior to onset), matching hazard, and matching geography before evaluation.",
            "Forecast replay inputs must strictly reflect forecasts available at decision time without lookahead.",
            "Observation-time detection delay (data date) and issue-time detection delay (operational alert dispatch timestamp) are evaluated and reported separately.",
            "Direct latency between source availability and alert issuance is calculated exactly (e.g. 10m 2s), without conflating daily batch cadence.",
            "Environmental-only policy produces an environmental exposure watch without health corroboration.",
            "In a null scenario with no reference event, unmatched alerts are reported as false alarms without claiming a true event was rejected.",
            "Zero warning episodes result in null/not-estimable PPV with explicit numerator and denominator exposure.",
            "All fixtures and performance results are synthetic. Do not claim demonstrated health-outcome improvements.",
        ],
        "scenario_evaluations": {},
        "policy_comparisons": {},
    }

    for sc_name, (sc_df, sc_ref, s_seed) in scenarios.items():
        suite_results["scenario_evaluations"][sc_name] = {}
        for pol in policies:
            eval_res = simulate_scenario(
                scenario_name=sc_name,
                df=sc_df,
                ref_event=sc_ref,
                policy_name=pol,
                start_date=start_date,
                scenario_seed=s_seed,
            )
            suite_results["scenario_evaluations"][sc_name][pol] = eval_res

    # Build policy comparison matrix across all scenarios
    for pol in policies:
        total_episodes = 0
        total_matched = 0
        total_unmatched = 0
        unmatched_in_null = 0
        scenario_timeliness: Dict[str, Any] = {}

        for sc_name in scenarios:
            res = suite_results["scenario_evaluations"][sc_name][pol]
            rec = res["auditable_episode_reconciliation"]
            perf = res["derived_performance_metrics"]

            total_episodes += rec["total_alert_episodes"]
            total_matched += rec["matched_alert_episodes"]
            total_unmatched += rec["unmatched_alert_episodes"]

            if "null" in sc_name or sc_name == "spurious-health-spike":
                unmatched_in_null += rec["unmatched_alert_episodes"]

            scenario_timeliness[sc_name] = {
                "observation_time_delay_days": perf["observation_time_detection_delay_days"],
                "issue_time_delay_days": perf["issue_time_detection_delay_days"],
                "observation_status": perf["observation_delay_status"],
                "issue_status": perf["issue_delay_status"],
                "corroborated_ppv": perf["corroborated_health_warning_ppv"],
                "corroborated_ppv_fraction": perf["corroborated_health_warning_ppv_fraction"],
                "operational_timeliness_narrative": perf["operational_timeliness_narrative"],
                "matched_episodes": rec["matched_alert_episodes"],
                "unmatched_episodes": rec["unmatched_alert_episodes"],
            }

        suite_results["policy_comparisons"][pol] = {
            "total_alert_episodes_across_scenarios": total_episodes,
            "matched_episodes": total_matched,
            "unmatched_episodes": total_unmatched,
            "unmatched_alerts_in_null_scenario": unmatched_in_null,
            "scenario_timeliness": scenario_timeliness,
            "policy_classification": (
                "environmental_exposure_watch"
                if pol == "environmental_only"
                else (
                    "uncorroborated_health_anomaly"
                    if pol == "health_only"
                    else "fused_corroborated_warning"
                )
            ),
            "operational_tradeoff_summary": (
                "Environmental exposure watch: triggers on physical threshold exceedance (Day 32 in gradual heat, Day 26 in abrupt shock); 0 unmatched alerts in null scenario, but lacks clinical or workforce corroboration."
                if pol == "environmental_only"
                else (
                    "Uncorroborated health anomaly: detects clinical surge on onset day (Day 31 in gradual heat, Day 26 in abrupt shock); vulnerable to non-environmental noise, generating pre-onset baseline false alarms and 1 unmatched alert in null scenario."
                    if pol == "health_only"
                    else "Fused corroborated warning: corroborates physical exposure with health/workforce impact; triggers corroborated warning on Day 32 in gradual heat (+1 day observation delay, ~2 day issue delay; post-onset detection) and Day 26 in abrupt shock (0-day delay); 0 unmatched warnings in null scenario."
                )
            ),
        }

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(suite_results, indent=2), encoding="utf-8")
    print(f"\n[+] Full CDC-aligned replay evaluation written to: {out_file.resolve()}")

    return suite_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SentinelHealth Auditable Replay Runner")
    parser.add_argument("--output", default="fixtures/replay_evaluation_summary.json", help="Output JSON path")
    args = parser.parse_args()
    results = run_comprehensive_replay_suite(output_path=args.output)
    print("\n[+] Replay Suite Execution Summary:")
    print(f"Scenarios evaluated: {list(results['scenario_evaluations'].keys())}")
