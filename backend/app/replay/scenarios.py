"""Deterministic synthetic scenario generators for SentinelHealth surveillance replay evaluation.

Phase 4 Validation Suite (15 Benchmark Scenarios):
Version: 0.3.0
Provenance:
- Summer heat scenarios anchored to summer dates (June-July 2026).
- Winter air quality scenarios anchored to winter inversion dates (November-December 2026).
- Deterministic random seeds with fixed pseudo-random number generator state.
- Explicit signal status ('valid', 'missing', 'stale', 'quarantined', 'suppressed').
- Ground truth reference events include hazard type and environmental attribution labels.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

SCENARIO_GENERATOR_VERSION = "0.3.0"


class ScenarioGenerator:
    """Generates synthetic signal records and reference ground-truth events."""

    # ──────────────────────────────────────────────────────────────────────────
    # Scenario 1: Gradual Heat Wave
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def generate_heat_gradual_scenario(
        start_date: Optional[datetime] = None,
        days: int = 45,
        seed: int = 42,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Gradual seasonal heatwave with multi-day thermal accumulation and secondary workforce morbidity."""
        if start_date is None:
            start_date = datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
        np.random.seed(seed)
        records = []

        # Baseline: days 0-30, Heat Wave: days 31-38, Post-event: days 39-45
        event_start_day = 31  # 2026-07-02
        event_end_day = 38    # 2026-07-09

        for d in range(days):
            current_day = start_date + timedelta(days=d)
            is_event = event_start_day <= d <= event_end_day

            base_temp = 32.0 + 2.0 * math.sin(d / 7.0)
            noise_temp = float(np.random.normal(0, 0.8))
            temp = (base_temp + noise_temp) + (9.0 if is_event else 0.0)

            records.append({
                "timestamp": current_day,
                "metric_code": "apparent_temperature",
                "signal_family": "environmental",
                "value": round(temp, 2),
                "unit": "celsius",
                "contributor_count": None,
                "exposure": None,
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

            base_health = 12.0 + (1.5 if current_day.weekday() in [0, 1] else 0.0)
            health_mult = 2.8 if is_event else 1.0
            health_count = int(np.random.poisson(base_health * health_mult))

            records.append({
                "timestamp": current_day,
                "metric_code": "heat_exhaustion_contacts",
                "signal_family": "clinical_service",
                "value": health_count,
                "unit": "encounters",
                "contributor_count": health_count,
                "exposure": 1500,
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

            base_absence = 22.0 + (3.0 if current_day.weekday() == 0 else 0.0)
            abs_mult = 3.2 if is_event else 1.0
            abs_count = int(np.random.poisson(base_absence * abs_mult))

            records.append({
                "timestamp": current_day,
                "metric_code": "sickness_absence_worker_days",
                "signal_family": "workforce",
                "value": abs_count,
                "unit": "worker_days",
                "contributor_count": abs_count,
                "exposure": 3400,
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

        df = pd.DataFrame(records)

        onset_dt = start_date + timedelta(days=event_start_day)
        end_dt = start_date + timedelta(days=event_end_day)
        target_action_dt = onset_dt - timedelta(days=1)

        reference_event = {
            "event_id": "REF-EVT-HEAT-GRADUAL-2026",
            "hazard": "heat_illness",
            "event_type": "gradual_heatwave",
            "environmental_attribution": "extreme_heat",
            "onset_at": onset_dt.isoformat(),
            "end_at": end_dt.isoformat(),
            "severity": "warning",
            "description": "Gradual seasonal heatwave with elevated apparent temperature and secondary workforce morbidity",
            "earliest_useful_action_at": target_action_dt.isoformat(),
        }

        return df, reference_event

    # ──────────────────────────────────────────────────────────────────────────
    # Scenario 2: Abrupt Extreme Heat
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def generate_heat_abrupt_extreme_scenario(
        start_date: Optional[datetime] = None,
        days: int = 48,
        seed: int = 101,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Acute extreme heat spike exceeding 43C apparent temperature on July 15."""
        if start_date is None:
            start_date = datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
        np.random.seed(seed)
        records = []

        # Day 44 is 2026-07-15
        event_start_day = 44
        event_end_day = 46

        for d in range(days):
            current_day = start_date + timedelta(days=d)
            is_event = event_start_day <= d <= event_end_day

            base_temp = 33.5
            noise_temp = float(np.random.normal(0, 0.6))
            temp = (base_temp + noise_temp) + (11.5 if is_event else 0.0)

            records.append({
                "timestamp": current_day,
                "metric_code": "apparent_temperature",
                "signal_family": "environmental",
                "value": round(temp, 2),
                "unit": "celsius",
                "contributor_count": None,
                "exposure": None,
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

            base_health = 10.0
            health_mult = 4.5 if is_event else 1.0
            health_count = int(np.random.poisson(base_health * health_mult))

            records.append({
                "timestamp": current_day,
                "metric_code": "heat_exhaustion_contacts",
                "signal_family": "clinical_service",
                "value": health_count,
                "unit": "encounters",
                "contributor_count": health_count,
                "exposure": 1500,
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

            base_absence = 20.0
            abs_mult = 3.8 if is_event else 1.0
            abs_count = int(np.random.poisson(base_absence * abs_mult))

            records.append({
                "timestamp": current_day,
                "metric_code": "sickness_absence_worker_days",
                "signal_family": "workforce",
                "value": abs_count,
                "unit": "worker_days",
                "contributor_count": abs_count,
                "exposure": 3400,
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

        df = pd.DataFrame(records)

        onset_dt = start_date + timedelta(days=event_start_day, hours=12)  # 2026-07-15 12:00
        end_dt = start_date + timedelta(days=event_end_day)
        target_action_dt = start_date + timedelta(days=event_start_day)

        reference_event = {
            "event_id": "REF-EVT-HEAT-ABRUPT-2026",
            "hazard": "heat_illness",
            "event_type": "abrupt_heat_shock",
            "environmental_attribution": "extreme_heat",
            "onset_at": onset_dt.isoformat(),
            "end_at": end_dt.isoformat(),
            "severity": "critical",
            "description": "Acute extreme heat spike exceeding 43C apparent temperature with rapid clinic surge",
            "earliest_useful_action_at": target_action_dt.isoformat(),
        }

        return df, reference_event

    # ──────────────────────────────────────────────────────────────────────────
    # Scenario 3: Heat Exposure Without Health Corroboration
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def generate_heat_exposure_without_health_scenario(
        start_date: Optional[datetime] = None,
        days: int = 45,
        seed: int = 301,
    ) -> Tuple[pd.DataFrame, Optional[Dict[str, Any]]]:
        """Extreme heat (T > 41C) on days 25-30 without clinic or workforce elevation.
        Emits environmental_watch; health counts stay strictly within nominal baseline (z < 1.0).
        Verifies zero false corroborated warnings are issued."""
        if start_date is None:
            start_date = datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
        np.random.seed(seed)
        records = []

        heat_start_day = 25
        heat_end_day = 30

        for d in range(days):
            current_day = start_date + timedelta(days=d)
            is_heat = heat_start_day <= d <= heat_end_day

            base_temp = 33.0
            noise_temp = float(np.random.normal(0, 0.6))
            temp = base_temp + noise_temp + (8.5 if is_heat else 0.0)

            records.append({
                "timestamp": current_day,
                "metric_code": "apparent_temperature",
                "signal_family": "environmental",
                "value": round(temp, 2),
                "unit": "celsius",
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

            # Health and absence remain strictly at nominal baseline (z < 1.0)
            health_count = min(13, max(8, int(np.random.poisson(10.0))))
            records.append({
                "timestamp": current_day,
                "metric_code": "heat_exhaustion_contacts",
                "signal_family": "clinical_service",
                "value": health_count,
                "unit": "encounters",
                "contributor_count": health_count,
                "exposure": 1500,
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

            abs_count = min(22, max(16, int(np.random.poisson(19.0))))
            records.append({
                "timestamp": current_day,
                "metric_code": "sickness_absence_worker_days",
                "signal_family": "workforce",
                "value": abs_count,
                "unit": "worker_days",
                "contributor_count": abs_count,
                "exposure": 3400,
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

        df = pd.DataFrame(records)
        return df, None

    # ──────────────────────────────────────────────────────────────────────────
    # Scenario 4: Health Spike Without Heat Exposure (Spurious Health Spike)
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def generate_spurious_health_spike_scenario(
        start_date: Optional[datetime] = None,
        days: int = 45,
        seed: int = 202,
    ) -> Tuple[pd.DataFrame, Optional[Dict[str, Any]]]:
        """Isolated health count surge on June 20 (Day 19) with completely normal ambient temperatures."""
        if start_date is None:
            start_date = datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
        np.random.seed(seed)
        records = []

        spike_day = 19

        for d in range(days):
            current_day = start_date + timedelta(days=d)
            is_spike = d == spike_day

            base_temp = 30.0 + 1.5 * math.sin(d / 10.0)
            noise_temp = float(np.random.normal(0, 0.7))
            temp = base_temp + noise_temp

            records.append({
                "timestamp": current_day,
                "metric_code": "apparent_temperature",
                "signal_family": "environmental",
                "value": round(temp, 2),
                "unit": "celsius",
                "contributor_count": None,
                "exposure": None,
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

            base_health = 11.0
            health_count = int(np.random.poisson(base_health * (4.2 if is_spike else 1.0)))

            records.append({
                "timestamp": current_day,
                "metric_code": "heat_exhaustion_contacts",
                "signal_family": "clinical_service",
                "value": health_count,
                "unit": "encounters",
                "contributor_count": health_count,
                "exposure": 1500,
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

            base_absence = 21.0
            abs_count = int(np.random.poisson(base_absence))

            records.append({
                "timestamp": current_day,
                "metric_code": "sickness_absence_worker_days",
                "signal_family": "workforce",
                "value": abs_count,
                "unit": "worker_days",
                "contributor_count": abs_count,
                "exposure": 3400,
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

        df = pd.DataFrame(records)
        return df, None

    # ──────────────────────────────────────────────────────────────────────────
    # Scenario 5: Concurrent Pollution and Respiratory Surge
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def generate_air_quality_respiratory_surge_scenario(
        start_date: Optional[datetime] = None,
        days: int = 45,
        seed: int = 501,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Winter particulate stagnation surge (> 140 ug/m3) on Nov 27 corroborated by acute respiratory encounters."""
        if start_date is None:
            start_date = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        np.random.seed(seed)
        records = []

        # Day 26 from Nov 1 is Nov 27
        event_start_day = 26
        event_end_day = 32

        for d in range(days):
            current_day = start_date + timedelta(days=d)
            is_event = event_start_day <= d <= event_end_day

            base_pm = 38.0 + 3.0 * math.sin(d / 6.0)
            noise_pm = float(np.random.normal(0, 3.5))
            pm25 = base_pm + noise_pm + (105.0 if is_event else 0.0)
            pm25 = max(10.0, round(pm25, 1))

            records.append({
                "timestamp": current_day,
                "metric_code": "pm25_concentration",
                "signal_family": "environmental",
                "value": pm25,
                "unit": "ug/m3",
                "contributor_count": None,
                "exposure": None,
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

            base_eu_aqi = 25.0
            eu_aqi = base_eu_aqi + (65.0 if is_event else 5.0)
            records.append({
                "timestamp": current_day,
                "metric_code": "aqi_eu",
                "signal_family": "environmental",
                "value": round(eu_aqi, 1),
                "unit": "index_points",
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

            base_resp = 12.0
            resp_mult = 3.6 if is_event else 1.0
            resp_count = int(np.random.poisson(base_resp * resp_mult))

            records.append({
                "timestamp": current_day,
                "metric_code": "acute_respiratory_contacts",
                "signal_family": "clinical_service",
                "value": resp_count,
                "unit": "encounters",
                "contributor_count": resp_count,
                "exposure": 50000,
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

            base_abs = 8.0
            abs_mult = 3.0 if is_event else 1.0
            abs_days = int(np.random.poisson(base_abs * abs_mult))

            records.append({
                "timestamp": current_day,
                "metric_code": "respiratory_sickness_absence_days",
                "signal_family": "workforce",
                "value": abs_days,
                "unit": "worker_days",
                "contributor_count": abs_days,
                "exposure": 3400,
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

        df = pd.DataFrame(records)

        onset_dt = start_date + timedelta(days=event_start_day)
        end_dt = start_date + timedelta(days=event_end_day)
        target_action_dt = onset_dt - timedelta(days=1)

        reference_event = {
            "event_id": "REF-EVT-AIR-QUALITY-SURGE-2026",
            "hazard": "respiratory_air_quality",
            "event_type": "winter_particulate_inversion",
            "environmental_attribution": "particulate_stagnation",
            "onset_at": onset_dt.isoformat(),
            "end_at": end_dt.isoformat(),
            "severity": "critical",
            "description": "Winter air quality thermal inversion with sustained PM2.5 > 140 ug/m3 and corroborated clinic surge",
            "earliest_useful_action_at": target_action_dt.isoformat(),
        }

        return df, reference_event

    # ──────────────────────────────────────────────────────────────────────────
    # Scenario 6: Pollution Without Health Corroboration
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def generate_air_quality_stagnation_without_health_scenario(
        start_date: Optional[datetime] = None,
        days: int = 45,
        seed: int = 601,
    ) -> Tuple[pd.DataFrame, Optional[Dict[str, Any]]]:
        """Pollution exceedance (PM2.5 >= 60 ug/m3) on Nov 26-30 without health surge.
        Emits environmental_watch; health encounters clamped at nominal baseline (z < 1.0)."""
        if start_date is None:
            start_date = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        np.random.seed(seed)
        records = []

        inversion_start_day = 25
        inversion_end_day = 30

        for d in range(days):
            current_day = start_date + timedelta(days=d)
            is_inversion = inversion_start_day <= d <= inversion_end_day

            base_pm = 32.0
            noise_pm = float(np.random.normal(0, 3.0))
            pm25 = base_pm + noise_pm + (65.0 if is_inversion else 0.0)
            pm25 = max(10.0, round(pm25, 1))

            records.append({
                "timestamp": current_day,
                "metric_code": "pm25_concentration",
                "signal_family": "environmental",
                "value": pm25,
                "unit": "ug/m3",
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

            # Health contacts strictly within nominal baseline
            resp_count = min(13, max(8, int(np.random.poisson(10.0))))

            records.append({
                "timestamp": current_day,
                "metric_code": "acute_respiratory_contacts",
                "signal_family": "clinical_service",
                "value": resp_count,
                "unit": "encounters",
                "contributor_count": resp_count,
                "exposure": 50000,
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

        df = pd.DataFrame(records)
        return df, None

    # ──────────────────────────────────────────────────────────────────────────
    # Scenario 7: Respiratory Surge Without Pollution (Restored Ground Truth Event)
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def generate_respiratory_outbreak_without_pollution_scenario(
        start_date: Optional[datetime] = None,
        days: int = 45,
        seed: int = 701,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Respiratory clinical surge starting Nov 18 occurring during clean air conditions.
        Reference ground truth event: real syndromic outbreak (viral/infectious), unattributed to air pollution."""
        if start_date is None:
            start_date = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        np.random.seed(seed)
        records = []

        # Day 17 from Nov 1 is Nov 18
        outbreak_start_day = 17
        outbreak_end_day = 23

        for d in range(days):
            current_day = start_date + timedelta(days=d)
            is_outbreak = outbreak_start_day <= d <= outbreak_end_day

            base_pm = 25.0
            noise_pm = float(np.random.normal(0, 2.0))
            pm25 = max(10.0, round(base_pm + noise_pm, 1))

            records.append({
                "timestamp": current_day,
                "metric_code": "pm25_concentration",
                "signal_family": "environmental",
                "value": pm25,
                "unit": "ug/m3",
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

            base_resp = 11.0
            resp_mult = 3.8 if is_outbreak else 1.0
            resp_count = int(np.random.poisson(base_resp * resp_mult))

            records.append({
                "timestamp": current_day,
                "metric_code": "acute_respiratory_contacts",
                "signal_family": "clinical_service",
                "value": resp_count,
                "unit": "encounters",
                "contributor_count": resp_count,
                "exposure": 50000,
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

        df = pd.DataFrame(records)

        onset_dt = start_date + timedelta(days=outbreak_start_day)  # 2026-11-18
        end_dt = start_date + timedelta(days=outbreak_end_day)      # 2026-11-24
        target_action_dt = onset_dt - timedelta(days=1)

        reference_event = {
            "event_id": "REF-EVT-RESP-OUTBREAK-2026",
            "hazard": "respiratory_air_quality",
            "event_type": "clinical_respiratory_outbreak",
            "environmental_attribution": "unattributed_clean_air",
            "onset_at": onset_dt.isoformat(),
            "end_at": end_dt.isoformat(),
            "severity": "warning",
            "description": "Syndromic acute respiratory surge occurring in clean air (unattributed to particulate pollution)",
            "earliest_useful_action_at": target_action_dt.isoformat(),
        }

        return df, reference_event

    # ──────────────────────────────────────────────────────────────────────────
    # Scenario 8: Stable Null Baseline
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def generate_stable_null_baseline_scenario(
        start_date: Optional[datetime] = None,
        days: int = 45,
        seed: int = 801,
    ) -> Tuple[pd.DataFrame, Optional[Dict[str, Any]]]:
        """Null hypothesis benchmark: nominal temperature, clean air, stable baseline health across 45 days."""
        if start_date is None:
            start_date = datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
        np.random.seed(seed)
        records = []

        for d in range(days):
            current_day = start_date + timedelta(days=d)
            temp = round(29.0 + float(np.random.normal(0, 0.7)), 2)
            pm25 = round(28.0 + float(np.random.normal(0, 2.5)), 1)
            resp_count = min(13, max(7, int(np.random.poisson(10.0))))
            heat_count = min(11, max(5, int(np.random.poisson(8.0))))

            records.append({
                "timestamp": current_day,
                "metric_code": "apparent_temperature",
                "signal_family": "environmental",
                "value": temp,
                "unit": "celsius",
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })
            records.append({
                "timestamp": current_day,
                "metric_code": "pm25_concentration",
                "signal_family": "environmental",
                "value": pm25,
                "unit": "ug/m3",
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })
            records.append({
                "timestamp": current_day,
                "metric_code": "heat_exhaustion_contacts",
                "signal_family": "clinical_service",
                "value": heat_count,
                "unit": "encounters",
                "contributor_count": heat_count,
                "exposure": 1500,
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })
            records.append({
                "timestamp": current_day,
                "metric_code": "acute_respiratory_contacts",
                "signal_family": "clinical_service",
                "value": resp_count,
                "unit": "encounters",
                "contributor_count": resp_count,
                "exposure": 50000,
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

        df = pd.DataFrame(records)
        return df, None

    # Backward compatibility alias
    generate_air_quality_null_scenario = generate_stable_null_baseline_scenario

    # ──────────────────────────────────────────────────────────────────────────
    # Scenario 9: Missing Environmental Input
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def generate_missing_environmental_input_scenario(
        start_date: Optional[datetime] = None,
        days: int = 45,
        seed: int = 902,
    ) -> Tuple[pd.DataFrame, Optional[Dict[str, Any]]]:
        """Upstream weather/pollution sensor feed drops out on days 20-25.
        Injects a real health surge on day 22: verifies the health anomaly is NOT dropped,
        while environmental data-gap status ('missing_input') is visibly logged."""
        if start_date is None:
            start_date = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        np.random.seed(seed)
        records = []

        for d in range(days):
            current_day = start_date + timedelta(days=d)
            is_dropout = 20 <= d <= 25
            is_health_surge = d == 22

            records.append({
                "timestamp": current_day,
                "metric_code": "pm25_concentration",
                "signal_family": "environmental",
                "value": None if is_dropout else round(30.0 + float(np.random.normal(0, 2.0)), 1),
                "unit": "ug/m3",
                "geography_id": "DIST-DHANPUR",
                "status": "missing" if is_dropout else "valid",
            })

            resp_count = 45 if is_health_surge else int(np.random.poisson(11.0))
            records.append({
                "timestamp": current_day,
                "metric_code": "acute_respiratory_contacts",
                "signal_family": "clinical_service",
                "value": resp_count,
                "unit": "encounters",
                "contributor_count": resp_count,
                "exposure": 50000,
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

        df = pd.DataFrame(records)
        return df, None

    # ──────────────────────────────────────────────────────────────────────────
    # Scenario 10: Missing Health Input
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def generate_missing_health_input_scenario(
        start_date: Optional[datetime] = None,
        days: int = 45,
        seed: int = 903,
    ) -> Tuple[pd.DataFrame, Optional[Dict[str, Any]]]:
        """EMR syndromic transmission pipeline is offline on days 20-25.
        PM2.5 spikes to 110 ug/m3 on day 22. Verifies environmental watch triggers, but corroborated warning is withheld."""
        if start_date is None:
            start_date = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        np.random.seed(seed)
        records = []

        for d in range(days):
            current_day = start_date + timedelta(days=d)
            is_emr_down = 20 <= d <= 25
            pm25 = 110.0 if d == 22 else 32.0

            records.append({
                "timestamp": current_day,
                "metric_code": "pm25_concentration",
                "signal_family": "environmental",
                "value": pm25,
                "unit": "ug/m3",
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

            records.append({
                "timestamp": current_day,
                "metric_code": "acute_respiratory_contacts",
                "signal_family": "clinical_service",
                "value": None if is_emr_down else int(np.random.poisson(12.0)),
                "unit": "encounters",
                "contributor_count": None if is_emr_down else 12,
                "exposure": 50000,
                "geography_id": "DIST-DHANPUR",
                "status": "missing" if is_emr_down else "valid",
            })

        df = pd.DataFrame(records)
        return df, None

    # ──────────────────────────────────────────────────────────────────────────
    # Scenario 11: Stale and Quarantined Records
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def generate_stale_quarantined_records_scenario(
        start_date: Optional[datetime] = None,
        days: int = 45,
        seed: int = 901,
    ) -> Tuple[pd.DataFrame, Optional[Dict[str, Any]]]:
        """Stale sensor readings (> 360m old) and QA-quarantined hardware logs.
        Verifies system ignores stale/quarantined data from alert triggering."""
        if start_date is None:
            start_date = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        np.random.seed(seed)
        records = []

        for d in range(days):
            current_day = start_date + timedelta(days=d)
            is_stale_day = (20 <= d <= 24)
            is_quarantined_day = (25 <= d <= 28)

            pm_status = "stale" if is_stale_day else ("quarantined" if is_quarantined_day else "valid")
            pm25 = 125.0 if (is_stale_day or is_quarantined_day) else 30.0

            records.append({
                "timestamp": current_day,
                "metric_code": "pm25_concentration",
                "signal_family": "environmental",
                "value": pm25,
                "unit": "ug/m3",
                "geography_id": "DIST-DHANPUR",
                "status": pm_status,
                "is_stale": is_stale_day,
                "is_quarantined": is_quarantined_day,
                "source_freshness_minutes": 480 if is_stale_day else 15,
            })

            records.append({
                "timestamp": current_day,
                "metric_code": "acute_respiratory_contacts",
                "signal_family": "clinical_service",
                "value": 10,
                "unit": "encounters",
                "contributor_count": 10,
                "exposure": 50000,
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

        df = pd.DataFrame(records)
        return df, None

    # Backward compatibility alias
    generate_air_quality_missing_stale_scenario = generate_stale_quarantined_records_scenario

    # ──────────────────────────────────────────────────────────────────────────
    # Scenario 12: Missing Denominator or Uncertain Geolocation
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def generate_missing_denominator_uncertain_geolocation_scenario(
        start_date: Optional[datetime] = None,
        days: int = 45,
        seed: int = 904,
    ) -> Tuple[pd.DataFrame, Optional[Dict[str, Any]]]:
        """Health encounters reported with missing exposure denominator or unassigned coordinates."""
        if start_date is None:
            start_date = datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
        np.random.seed(seed)
        records = []

        for d in range(days):
            current_day = start_date + timedelta(days=d)
            is_unmapped = (22 <= d <= 27)

            records.append({
                "timestamp": current_day,
                "metric_code": "apparent_temperature",
                "signal_family": "environmental",
                "value": round(32.0 + float(np.random.normal(0, 0.8)), 2),
                "unit": "celsius",
                "geography_id": None if is_unmapped else "DIST-DHANPUR",
                "status": "valid",
            })

            records.append({
                "timestamp": current_day,
                "metric_code": "heat_exhaustion_contacts",
                "signal_family": "clinical_service",
                "value": int(np.random.poisson(12.0)),
                "unit": "encounters",
                "contributor_count": 12,
                "exposure": None if is_unmapped else 1500,  # Missing denominator
                "geography_id": None if is_unmapped else "DIST-DHANPUR",
                "status": "valid",
            })

        df = pd.DataFrame(records)
        return df, None

    # ──────────────────────────────────────────────────────────────────────────
    # Scenario 13: Small Cells and Overlapping-Filter Disclosure Control
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def generate_small_cells_overlapping_disclosure_scenario(
        start_date: Optional[datetime] = None,
        days: int = 45,
        seed: int = 905,
    ) -> Tuple[pd.DataFrame, Optional[Dict[str, Any]]]:
        """Low cell counts (1 to 4 encounters) and small contributor pools (< 10).
        Verifies small-cell suppression rules suppress values while environmental values remain unmasked."""
        if start_date is None:
            start_date = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        np.random.seed(seed)
        records = []

        for d in range(days):
            current_day = start_date + timedelta(days=d)
            is_small_cell_day = (18 <= d <= 26)

            records.append({
                "timestamp": current_day,
                "metric_code": "pm25_concentration",
                "signal_family": "environmental",
                "value": 3.2 if is_small_cell_day else 35.0,  # Environmental values <= 4 NOT suppressed
                "unit": "ug/m3",
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

            resp_val = 2 if is_small_cell_day else int(np.random.poisson(12.0))
            contrib = 2 if is_small_cell_day else 20

            records.append({
                "timestamp": current_day,
                "metric_code": "acute_respiratory_contacts",
                "signal_family": "clinical_service",
                "value": resp_val,
                "unit": "encounters",
                "contributor_count": contrib,
                "exposure": 50000,
                "geography_id": "DIST-DHANPUR",
                "status": "suppressed" if is_small_cell_day else "valid",
                "is_suppressed": is_small_cell_day,
            })

        df = pd.DataFrame(records)
        return df, None

    # ──────────────────────────────────────────────────────────────────────────
    # Scenario 14: Duplicate, Revised, and Out-of-Order Records
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def generate_duplicate_revised_out_of_order_scenario(
        start_date: Optional[datetime] = None,
        days: int = 45,
        seed: int = 906,
    ) -> Tuple[pd.DataFrame, Optional[Dict[str, Any]]]:
        """Signal stream with repeated run keys, retroactive revisions, and non-chronological sorting."""
        if start_date is None:
            start_date = datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
        np.random.seed(seed)
        records = []

        for d in range(days):
            current_day = start_date + timedelta(days=d)

            records.append({
                "timestamp": current_day,
                "metric_code": "apparent_temperature",
                "signal_family": "environmental",
                "value": round(31.0 + float(np.random.normal(0, 0.5)), 2),
                "unit": "celsius",
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

            records.append({
                "timestamp": current_day,
                "metric_code": "sickness_absence_worker_days",
                "signal_family": "workforce",
                "value": int(np.random.poisson(18.0)),
                "unit": "worker_days",
                "contributor_count": 18,
                "exposure": 3400,
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

        # Inject intentional duplicate on day 15
        dup_record = {
            "timestamp": start_date + timedelta(days=15),
            "metric_code": "sickness_absence_worker_days",
            "signal_family": "workforce",
            "value": 18,
            "unit": "worker_days",
            "contributor_count": 18,
            "exposure": 3400,
            "geography_id": "DIST-DHANPUR",
            "status": "valid",
        }
        records.append(dup_record)

        df = pd.DataFrame(records)
        # Randomize order to test chronological sort requirement
        df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
        return df, None

    # ──────────────────────────────────────────────────────────────────────────
    # Scenario 15: Baseline Drift and Changing Exposure Denominators
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def generate_baseline_drift_changing_exposure_scenario(
        start_date: Optional[datetime] = None,
        days: int = 45,
        seed: int = 907,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Workforce plant doubles headcount (1500 to 3000) on day 22.
        Actual acute health event injected on day 35 (2026-07-06).
        Verifies Poisson baseline scales expected counts proportionally without false alarms,
        and accurately detects real surge after drift."""
        if start_date is None:
            start_date = datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
        np.random.seed(seed)
        records = []

        expansion_day = 22
        surge_day = 35

        for d in range(days):
            current_day = start_date + timedelta(days=d)
            is_expanded = d >= expansion_day
            current_exposure = 3000 if is_expanded else 1500

            records.append({
                "timestamp": current_day,
                "metric_code": "apparent_temperature",
                "signal_family": "environmental",
                "value": round(32.0 + float(np.random.normal(0, 0.6)), 2),
                "unit": "celsius",
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

            if d == surge_day:
                health_count = 68  # Real surge after drift
            else:
                base_count = 24 if is_expanded else 12
                health_count = int(np.random.poisson(base_count))

            records.append({
                "timestamp": current_day,
                "metric_code": "heat_exhaustion_contacts",
                "signal_family": "clinical_service",
                "value": health_count,
                "unit": "encounters",
                "contributor_count": health_count,
                "exposure": current_exposure,
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

        df = pd.DataFrame(records)

        onset_dt = start_date + timedelta(days=surge_day)
        end_dt = onset_dt + timedelta(days=2)
        target_action_dt = onset_dt - timedelta(days=1)

        reference_event = {
            "event_id": "REF-EVT-DRIFT-SURGE-2026",
            "hazard": "heat_illness",
            "event_type": "post_drift_clinical_surge",
            "environmental_attribution": "unattributed_normal_temp",
            "onset_at": onset_dt.isoformat(),
            "end_at": end_dt.isoformat(),
            "severity": "warning",
            "description": "Acute workplace clinic surge occurring after facility expansion and baseline shift",
            "earliest_useful_action_at": target_action_dt.isoformat(),
        }

        return df, reference_event
