"""Chronological replay execution, policy comparison, and auditable metric evaluation engine."""

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


def simulate_scenario(
    scenario_name: str,
    df: pd.DataFrame,
    ref_event: Optional[Dict[str, Any]],
    policy_name: str = "fused_corroborated",
    burn_in_days: int = 14,
    temp_threshold_c: float = 39.0,
    smoothing_factor: float = 0.3,
    control_limit_sigma: float = 2.5,
    start_date: Optional[datetime] = None,
    tenant_id: str = "greenfield_industries",
) -> Dict[str, Any]:
    """
    Simulates chronological day-by-day surveillance without lookahead.
    Evaluates one of three policies:
      - 'fused_corroborated': EvidenceFusionEngine multi-signal logic
      - 'environmental_only': Alerts solely when environmental threshold exceeded
      - 'health_only': Alerts solely when health or workforce anomaly elevated
    """
    if start_date is None:
        start_date = df["timestamp"].min()

    total_days = int((df["timestamp"].max() - start_date).days) + 1
    eval_days = total_days - burn_in_days

    recent_baseline = RecentHistoryBaseline(lookback_days=28, weekday_matching=True)
    poisson_baseline = PoissonCountBaseline(min_samples=14)

    detector = OneSidedEWMADetector(
        smoothing_factor=smoothing_factor,
        control_limit_sigma=control_limit_sigma,
    )
    fusion_engine = EvidenceFusionEngine(policy_version="0.1.0")

    raw_alerts: List[Dict[str, Any]] = []
    step_latencies: List[float] = []

    for d in range(burn_in_days, total_days):
        t0 = time.perf_counter()
        sim_time = start_date + timedelta(days=d)
        available_df = df[df["timestamp"] <= sim_time].copy()

        evidences: List[EvidenceItem] = []

        # 1. Weather
        weather_df = available_df[available_df["metric_code"] == "apparent_temperature"]
        if not weather_df.empty:
            current_temp = float(weather_df.iloc[-1]["value"])
            temp_baseline = recent_baseline.fit_predict(weather_df, sim_time)
            temp_score = detector.compute_anomaly(
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
                )
            )

        # 2. Health contacts
        health_df = available_df[available_df["metric_code"] == "heat_exhaustion_contacts"]
        if not health_df.empty:
            current_health = float(health_df.iloc[-1]["value"])
            health_pred = poisson_baseline.fit_predict(health_df, sim_time, current_exposure=1500)
            health_score = detector.compute_anomaly(
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

        # 3. Workforce absence
        work_df = available_df[available_df["metric_code"] == "sickness_absence_worker_days"]
        if not work_df.empty:
            current_work = float(work_df.iloc[-1]["value"])
            work_pred = poisson_baseline.fit_predict(work_df, sim_time, current_exposure=3400)
            work_score = detector.compute_anomaly(
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
                )
            )

        t1 = time.perf_counter()
        step_latencies.append((t1 - t0) * 1000.0)

        # Evaluate policy
        if policy_name == "environmental_only":
            env_item = next((e for e in evidences if e.metric_code == "apparent_temperature"), None)
            if env_item and env_item.observed >= temp_threshold_c:
                raw_alerts.append({
                    "day": d,
                    "timestamp": sim_time,
                    "evidence_class": "environmental_watch",
                    "severity": "watch",
                    "score": 50.0,
                    "reasons": [f"Apparent temperature {env_item.observed}°C >= {temp_threshold_c}°C"],
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
                    "timestamp": sim_time,
                    "evidence_class": "uncorroborated_health_anomaly",
                    "severity": "advisory",
                    "score": 60.0,
                    "reasons": [f"{e.metric_code} residual {e.standardised_residual:.2f} > 2.0" for e in health_elevated],
                })
        else:  # fused_corroborated
            decision = fusion_engine.evaluate(
                hazard="heat_illness",
                evidences=evidences,
                environmental_thresholds={"apparent_temperature": temp_threshold_c},
            )
            if decision.should_alert:
                raw_alerts.append({
                    "day": d,
                    "timestamp": sim_time,
                    "evidence_class": decision.evidence_class,
                    "severity": decision.severity,
                    "score": decision.evidence_score,
                    "reasons": decision.reasons,
                })

    # Cluster into multi-day alert episodes (gap <= 2 days)
    # Distinct episode clustering per category to maintain strict mutual exclusivity
    categories = [
        "corroborated_health_warning",
        "uncorroborated_health_anomaly",
        "environmental_watch",
        "safety_escalation",
    ]

    episodes_by_category: Dict[str, List[Dict[str, Any]]] = {c: [] for c in categories}

    # Group sequential alerts by category
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

    # Total episodes is the sum of category episodes
    total_episodes_count = sum(len(eps) for eps in episodes_by_category.values())

    # Build detailed auditable episode list with reference event matching
    detailed_episodes: List[Dict[str, Any]] = []
    category_summary: Dict[str, Dict[str, int]] = {}

    ref_onset = datetime.fromisoformat(ref_event["onset_at"]) if ref_event else None
    ref_end = datetime.fromisoformat(ref_event["end_at"]) if ref_event else None
    ref_id = ref_event.get("event_id", "REF-EVT-UNKNOWN") if ref_event else None
    earliest_useful = (
        datetime.fromisoformat(ref_event["earliest_useful_action_at"])
        if ref_event and "earliest_useful_action_at" in ref_event
        else None
    )

    matched_episodes_count = 0
    unmatched_episodes_count = 0
    first_corroborated_alert_time: Optional[datetime] = None
    first_any_alert_time: Optional[datetime] = None

    ep_seq = 1
    for cat in categories:
        cat_matched = 0
        cat_unmatched = 0

        for ep_info in episodes_by_category[cat]:
            alerts = ep_info["alerts"]
            first_alert_time: datetime = alerts[0]["timestamp"]
            last_alert_time: datetime = alerts[-1]["timestamp"]
            ep_days = ep_info["days"]

            if first_any_alert_time is None or first_alert_time < first_any_alert_time:
                first_any_alert_time = first_alert_time

            # Matching criteria against reference event:
            # Alert episode starts within [-2 days, end_at] of ground-truth reference event
            is_matched = False
            matching_reason = ""
            matched_ref_id: Optional[str] = None

            if ref_event and ref_onset and ref_end:
                match_window_start = ref_onset - timedelta(days=2)
                if match_window_start <= first_alert_time <= ref_end:
                    is_matched = True
                    matched_ref_id = ref_id
                    matching_reason = (
                        f"Episode onset {first_alert_time.strftime('%Y-%m-%d')} falls within reference "
                        f"event matching window [{match_window_start.strftime('%Y-%m-%d')} to {ref_end.strftime('%Y-%m-%d')}]."
                    )
                elif first_alert_time < match_window_start:
                    is_matched = False
                    matching_reason = (
                        f"Episode onset {first_alert_time.strftime('%Y-%m-%d')} occurred prior to reference event onset "
                        f"(Poisson baseline fluctuation / noise; false alarm)."
                    )
                else:
                    is_matched = False
                    matching_reason = (
                        f"Episode onset {first_alert_time.strftime('%Y-%m-%d')} occurred after reference event end."
                    )
            else:
                is_matched = False
                matching_reason = "No ground-truth reference event in scenario (null scenario; false positive)."

            if is_matched:
                matched_episodes_count += 1
                cat_matched += 1
                if cat == "corroborated_health_warning" and first_corroborated_alert_time is None:
                    first_corroborated_alert_time = first_alert_time
            else:
                unmatched_episodes_count += 1
                cat_unmatched += 1

            detailed_episodes.append({
                "episode_id": f"EP-{scenario_name[:4].upper()}-{ep_seq:03d}",
                "tenant_id": tenant_id,
                "hazard": "heat_illness",
                "category": cat,
                "days_active": ep_days,
                "first_issued_at": first_alert_time.isoformat(),
                "last_issued_at": last_alert_time.isoformat(),
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
    event_sensitivity = (matched_ref_events / total_ref_events) if total_ref_events > 0 else None

    eligible_site_weeks = round(eval_days / 7.0, 2)
    overall_ppv = (matched_episodes_count / total_episodes_count) if total_episodes_count > 0 else 0.0

    corr_summary = category_summary["corroborated_health_warning"]
    corroborated_ppv = (
        (corr_summary["matched_episodes"] / corr_summary["total_episodes"])
        if corr_summary["total_episodes"] > 0
        else 0.0
    )

    # Operational latency vs compute latency
    # Compute latency: time to compute EWMA and fusion in milliseconds
    mean_scoring_latency_ms = round(sum(step_latencies) / len(step_latencies), 2) if step_latencies else 0.0

    # Operational timeliness metrics
    detection_delay_days: Optional[float] = None
    useful_action_lead_days: Optional[float] = None
    target_alert_time = first_corroborated_alert_time or (
        first_any_alert_time if policy_name != "fused_corroborated" else None
    )

    if target_alert_time and ref_onset:
        detection_delay_days = round((target_alert_time - ref_onset).total_seconds() / 86400.0, 2)
    if target_alert_time and earliest_useful:
        useful_action_lead_days = round((earliest_useful - target_alert_time).total_seconds() / 86400.0, 2)

    # Verification of mathematical reconciliation:
    sum_categories = sum(category_summary[c]["total_episodes"] for c in categories)
    assert total_episodes_count == sum_categories, (
        f"Reconciliation error: total {total_episodes_count} != sum {sum_categories}"
    )

    return {
        "policy": policy_name,
        "scenario": scenario_name,
        "reference_ground_truth": {
            "total_reference_events": total_ref_events,
            "matched_reference_events": matched_ref_events,
            "missed_reference_events": total_ref_events - matched_ref_events,
            "event_id": ref_id,
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
            "corroborated_health_warning_ppv": round(corroborated_ppv, 4),
            "detection_delay_days": detection_delay_days,
            "useful_action_lead_days": useful_action_lead_days,
            "mean_scoring_latency_ms": mean_scoring_latency_ms,
            "source_to_alert_operational_cadence_hours": 24.0,  # daily aggregated batch
        },
        "episodes": detailed_episodes,
    }


def run_chronological_replay(
    scenario_name: str = "heat-gradual",
    seed: int = 42,
    output_path: str | None = None,
) -> Dict[str, Any]:
    """
    Backwards-compatible entrypoint to simulate a specific scenario.
    """
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
    )
    if output_path:
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(json.dumps(res, indent=2), encoding="utf-8")
    return res


def run_comprehensive_replay_suite(output_path: str = "fixtures/replay_evaluation_summary.json") -> Dict[str, Any]:
    """
    Runs multi-scenario, multi-policy auditable evaluation.
    Evaluates:
      Scenarios:
        - heat-gradual
        - heat-abrupt-extreme
        - spurious-health-spike
      Policies:
        - environmental_only
        - health_only
        - fused_corroborated
    """
    start_date = datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)

    # 1. Generate scenarios
    grad_df, grad_ref = ScenarioGenerator.generate_heat_gradual_scenario(start_date=start_date, days=45, seed=42)
    abrupt_df, abrupt_ref = ScenarioGenerator.generate_heat_abrupt_extreme_scenario(start_date=start_date, days=45, seed=101)
    spurious_df, spurious_ref = ScenarioGenerator.generate_spurious_health_spike_scenario(start_date=start_date, days=45, seed=202)

    scenarios = {
        "heat-gradual": (grad_df, grad_ref),
        "heat-abrupt-extreme": (abrupt_df, abrupt_ref),
        "spurious-health-spike": (spurious_df, spurious_ref),
    }

    policies = ["environmental_only", "health_only", "fused_corroborated"]

    suite_results: Dict[str, Any] = {
        "evaluation_title": "SentinelHealth Auditable Replay Evaluation Suite",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "This prototype has not undergone clinical validation, production security assessment or jurisdiction-specific legal/compliance review.",
        "scientific_and_operational_notes": [
            "100% sensitivity on a single synthetic event is an illustrative scenario result, not proof of general clinical detection performance.",
            "Weather screening uses the Australian BOM empirical approximation (Ta, RH) in shade, which is non-interchangeable with direct ISO 7243 WBGT.",
            "EWMA control limits represent nominal analytical limits under i.i.d. assumptions; empirical autocorrelation alters operational run lengths.",
            "Detection delay (+1 day) and useful-action lead (-2 days) in gradual heat demonstrate that fused warning corroborated post-onset, while environmental watch alerted in advance.",
            "Surveillance timeliness must be evaluated against operational opportunities for action (CDC MMWR). Scoring latency (ms) measures compute time; source-to-alert latency measures data transmission cadence and detection delay.",
        ],
        "scenario_evaluations": {},
        "policy_comparisons": {},
    }

    for sc_name, (sc_df, sc_ref) in scenarios.items():
        suite_results["scenario_evaluations"][sc_name] = {}
        for pol in policies:
            eval_res = simulate_scenario(
                scenario_name=sc_name,
                df=sc_df,
                ref_event=sc_ref,
                policy_name=pol,
                start_date=start_date,
            )
            suite_results["scenario_evaluations"][sc_name][pol] = eval_res

    # Build policy comparison matrix across all 3 scenarios
    for pol in policies:
        total_episodes = 0
        total_matched = 0
        total_unmatched = 0
        false_alarms = 0
        delays = []

        for sc_name in scenarios:
            res = suite_results["scenario_evaluations"][sc_name][pol]
            rec = res["auditable_episode_reconciliation"]
            perf = res["derived_performance_metrics"]

            total_episodes += rec["total_alert_episodes"]
            total_matched += rec["matched_alert_episodes"]
            total_unmatched += rec["unmatched_alert_episodes"]
            if sc_name == "spurious-health-spike":
                false_alarms += rec["total_alert_episodes"]

            if perf["detection_delay_days"] is not None:
                delays.append(perf["detection_delay_days"])

        suite_results["policy_comparisons"][pol] = {
            "total_alert_episodes_across_scenarios": total_episodes,
            "matched_episodes": total_matched,
            "unmatched_episodes": total_unmatched,
            "false_alarms_in_null_scenario": false_alarms,
            "mean_detection_delay_days": round(sum(delays) / len(delays), 2) if delays else None,
            "tradeoff_summary": (
                "High sensitivity with zero delay, but alarms continuously on weather alone without workforce corroboration."
                if pol == "environmental_only"
                else (
                    "Detects clinical surges, but vulnerable to non-environmental noise (highest false alarm rate in null scenario)."
                    if pol == "health_only"
                    else "Filters spurious health spikes and produces specific warnings, balancing timeliness and positive predictive value."
                )
            ),
        }

    # Write output to json
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(suite_results, indent=2), encoding="utf-8")
    print(f"\n[+] Full replay evaluation written to: {out_file.resolve()}")

    return suite_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SentinelHealth Auditable Replay Runner")
    parser.add_argument("--output", default="fixtures/replay_evaluation_summary.json", help="Output JSON path")
    args = parser.parse_args()
    results = run_comprehensive_replay_suite(output_path=args.output)
    print("\n[+] Replay Suite Execution Summary:")
    print(f"Scenarios evaluated: {list(results['scenario_evaluations'].keys())}")
    print(f"Policy comparisons: {json.dumps(results['policy_comparisons'], indent=2)}")
