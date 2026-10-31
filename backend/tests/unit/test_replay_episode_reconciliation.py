"""Automated mathematical reconciliation test for SentinelHealth replay evaluation.

Validates that every count, fraction, PPV, and event sensitivity reported in
replay_evaluation_summary.json exactly matches the programmatic aggregation of
replay_evaluation_episodes.json down to the exact integer.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest


@pytest.fixture
def replay_fixtures():
    base_dir = Path(__file__).resolve().parent.parent.parent / "fixtures"
    summary_path = base_dir / "replay_evaluation_summary.json"
    episodes_path = base_dir / "replay_evaluation_episodes.json"
    episodes_csv_path = base_dir / "replay_evaluation_episodes.csv"

    assert summary_path.exists(), f"Summary fixture missing at {summary_path}"
    assert episodes_path.exists(), f"Episodes fixture missing at {episodes_path}"
    assert episodes_csv_path.exists(), f"Episodes CSV fixture missing at {episodes_csv_path}"

    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)
    with open(episodes_path, "r", encoding="utf-8") as f:
        episodes = json.load(f)

    return summary, episodes


def test_episodes_json_matches_csv_count(replay_fixtures):
    """Verify that episodes JSON and CSV exports have identical record counts and non-empty rows."""
    summary, episodes = replay_fixtures
    base_dir = Path(__file__).resolve().parent.parent.parent / "fixtures"
    csv_lines = [line.strip() for line in (base_dir / "replay_evaluation_episodes.csv").read_text(encoding="utf-8").splitlines() if line.strip()]
    
    # Exclude header
    csv_rows_count = len(csv_lines) - 1
    assert len(episodes) == csv_rows_count, f"JSON episodes count {len(episodes)} != CSV rows count {csv_rows_count}"
    assert summary["total_episodes_evaluated"] == len(episodes)


def test_policy_comparison_reconciliation_from_episodes(replay_fixtures):
    """Verify that every policy comparison metric in the summary is directly derivable from the episode list."""
    summary, episodes = replay_fixtures
    policies = ["environmental_only", "health_only", "fused_corroborated"]

    for pol in policies:
        pol_eps = [e for e in episodes if e["policy"] == pol]
        pol_summary = summary["policy_comparisons"][pol]

        # 1. Total episodes, matched, and unmatched
        assert pol_summary["total_alert_episodes_across_scenarios"] == len(pol_eps)
        expected_matched = sum(1 for e in pol_eps if e["is_matched"])
        expected_unmatched = sum(1 for e in pol_eps if not e["is_matched"])
        assert pol_summary["matched_episodes"] == expected_matched
        assert pol_summary["unmatched_episodes"] == expected_unmatched

        # 2. Null scenario unmatched alerts
        expected_null_unmatched = sum(1 for e in pol_eps if e["scenario_name"] == "stable-null-baseline" and not e["is_matched"])
        assert pol_summary["unmatched_alerts_in_null_scenario"] == expected_null_unmatched
        # Stable null baseline must have exactly zero false alarms for fused and env
        if pol in ["fused_corroborated", "environmental_only"]:
            assert expected_null_unmatched == 0

        # 3. Alert class breakdown
        for cls_name, cls_data in pol_summary["alert_class_breakdown"].items():
            cls_eps = [e for e in pol_eps if e["alert_class"] == cls_name]
            assert cls_data["total_episodes"] == len(cls_eps)
            cls_mat = sum(1 for e in cls_eps if e["is_matched"])
            cls_unmat = sum(1 for e in cls_eps if not e["is_matched"])
            assert cls_data["matched_episodes"] == cls_mat
            assert cls_data["unmatched_episodes"] == cls_unmat
            if len(cls_eps) > 0:
                expected_ppv = round(cls_mat / len(cls_eps), 4)
                assert cls_data["ppv"] == expected_ppv
            else:
                assert cls_data["ppv"] is None

        # 4. Fused policy specific guarantees:
        if pol == "fused_corroborated":
            # Warning tier has 100% PPV and 0 unmatched false warnings
            warn_data = pol_summary["alert_class_breakdown"]["corroborated_health_warning"]
            assert warn_data["total_episodes"] == 3
            assert warn_data["matched_episodes"] == 3
            assert warn_data["unmatched_episodes"] == 0
            assert warn_data["ppv"] == 1.0
            assert pol_summary["crisis_warning_sensitivity"]["sensitivity"] == 1.0


def test_reference_event_sensitivity_counts_unique_events(replay_fixtures):
    """Verify that event sensitivity counts unique ground-truth events, not alert episodes."""
    summary, episodes = replay_fixtures
    all_ref_ids = {"REF-EVT-HEAT-GRADUAL-2026", "REF-EVT-HEAT-ABRUPT-2026", "REF-EVT-AIR-QUALITY-SURGE-2026", "REF-EVT-RESP-OUTBREAK-2026", "REF-EVT-DRIFT-SURGE-2026"}
    
    for pol in ["environmental_only", "health_only", "fused_corroborated"]:
        pol_eps = [e for e in episodes if e["policy"] == pol and e["is_matched"] and e["matched_reference_event_id"]]
        detected_events = set(e["matched_reference_event_id"] for e in pol_eps)
        
        pol_summary = summary["policy_comparisons"][pol]
        assert set(pol_summary["event_sensitivity"]["detected_reference_events"]) == detected_events
        assert pol_summary["event_sensitivity"]["total_reference_events"] == len(all_ref_ids)
        assert pol_summary["event_sensitivity"]["event_sensitivity"] == round(len(detected_events) / len(all_ref_ids), 4)

