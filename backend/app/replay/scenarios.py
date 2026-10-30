"""Deterministic synthetic scenario generators."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd


class ScenarioGenerator:
    """Generates synthetic signal records and reference ground-truth events."""

    @staticmethod
    def generate_heat_gradual_scenario(
        start_date: datetime,
        days: int = 45,
        seed: int = 42,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        np.random.seed(seed)
        records = []

        # Baseline: days 0-30, Heat Wave: days 31-38, Post-event: days 39-45
        event_start_day = 31
        event_end_day = 38

        for d in range(days):
            current_day = start_date + timedelta(days=d)
            is_event = event_start_day <= d <= event_end_day

            # Weather (Temp)
            base_temp = 32.0 + 2.0 * math.sin(d / 7.0)
            noise_temp = float(np.random.normal(0, 1.0))
            temp = (base_temp + noise_temp) + (9.0 if is_event else 0.0)

            records.append({
                "timestamp": current_day,
                "metric_code": "apparent_temperature",
                "signal_family": "environmental",
                "value": round(temp, 2),
                "unit": "celsius",
                "contributor_count": None,
                "exposure": None,
            })

            # Health Contacts (Poisson-like)
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
            })

            # Workforce Absence
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
            })

        df = pd.DataFrame(records)

        reference_event = {
            "event_id": "REF-EVT-HEAT-GRADUAL-2026",
            "hazard": "heat_illness",
            "onset_at": (start_date + timedelta(days=event_start_day)).isoformat(),
            "end_at": (start_date + timedelta(days=event_end_day)).isoformat(),
            "severity": "warning",
            "earliest_useful_action_at": (start_date + timedelta(days=event_start_day - 1)).isoformat(),
            "evidence_basis": "Ground truth simulated heat-wave exposure and health increase",
        }

        return df, reference_event

    @staticmethod
    def generate_heat_abrupt_extreme_scenario(
        start_date: datetime,
        days: int = 45,
        seed: int = 101,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Generates an abrupt, extreme heat shock scenario.
        Baseline: days 0-25.
        Abrupt spike: days 26-29 (temperatures jump immediately to 44°C+).
        Post-event: days 30-45.
        """
        np.random.seed(seed)
        records = []

        event_start_day = 26
        event_end_day = 29

        for d in range(days):
            current_day = start_date + timedelta(days=d)
            is_event = event_start_day <= d <= event_end_day

            # Weather (Abrupt jump from 31°C to 44.5°C)
            base_temp = 31.0 + 1.5 * math.sin(d / 7.0)
            noise_temp = float(np.random.normal(0, 0.8))
            temp = (base_temp + noise_temp) + (13.0 if is_event else 0.0)

            records.append({
                "timestamp": current_day,
                "metric_code": "apparent_temperature",
                "signal_family": "environmental",
                "value": round(temp, 2),
                "unit": "celsius",
                "contributor_count": None,
                "exposure": None,
            })

            # Health Contacts (Rapid doubling/tripling)
            base_health = 11.0 + (1.5 if current_day.weekday() in [0, 1] else 0.0)
            health_mult = 3.5 if is_event else 1.0
            health_count = int(np.random.poisson(base_health * health_mult))

            records.append({
                "timestamp": current_day,
                "metric_code": "heat_exhaustion_contacts",
                "signal_family": "clinical_service",
                "value": health_count,
                "unit": "encounters",
                "contributor_count": health_count,
                "exposure": 1500,
            })

            # Workforce Absence
            base_absence = 20.0 + (2.5 if current_day.weekday() == 0 else 0.0)
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
            })

        df = pd.DataFrame(records)

        reference_event = {
            "event_id": "REF-EVT-HEAT-ABRUPT-2026",
            "hazard": "heat_illness",
            "onset_at": (start_date + timedelta(days=event_start_day)).isoformat(),
            "end_at": (start_date + timedelta(days=event_end_day)).isoformat(),
            "severity": "critical",
            "earliest_useful_action_at": (start_date + timedelta(days=event_start_day - 1)).isoformat(),
            "evidence_basis": "Ground truth simulated abrupt extreme heat wave with rapid clinical surge",
        }

        return df, reference_event

    @staticmethod
    def generate_spurious_health_spike_scenario(
        start_date: datetime,
        days: int = 45,
        seed: int = 202,
    ) -> Tuple[pd.DataFrame, Dict[str, Any] | None]:
        """
        Generates a non-environmental spurious health / absence spike scenario.
        Weather remains normal (no heat hazard).
        An isolated non-heat illness or data reporting anomaly causes health/absence spike on days 21-23.
        Reference ground-truth heat event is None (null hypothesis testing for false alarms).
        """
        np.random.seed(seed)
        records = []

        spike_start_day = 21
        spike_end_day = 23

        for d in range(days):
            current_day = start_date + timedelta(days=d)
            is_spike = spike_start_day <= d <= spike_end_day

            # Weather (Normal mild summer, well below 39°C threshold: 28-33°C)
            base_temp = 30.0 + 2.0 * math.sin(d / 6.0)
            noise_temp = float(np.random.normal(0, 0.9))
            temp = base_temp + noise_temp

            records.append({
                "timestamp": current_day,
                "metric_code": "apparent_temperature",
                "signal_family": "environmental",
                "value": round(temp, 2),
                "unit": "celsius",
                "contributor_count": None,
                "exposure": None,
            })

            # Health Contacts (Isolated spike without environmental heat)
            base_health = 12.0
            health_mult = 3.0 if is_spike else 1.0
            health_count = int(np.random.poisson(base_health * health_mult))

            records.append({
                "timestamp": current_day,
                "metric_code": "heat_exhaustion_contacts",
                "signal_family": "clinical_service",
                "value": health_count,
                "unit": "encounters",
                "contributor_count": health_count,
                "exposure": 1500,
            })

            # Workforce Absence (Moderate elevation during spike)
            base_absence = 21.0
            abs_mult = 2.5 if is_spike else 1.0
            abs_count = int(np.random.poisson(base_absence * abs_mult))

            records.append({
                "timestamp": current_day,
                "metric_code": "sickness_absence_worker_days",
                "signal_family": "workforce",
                "value": abs_count,
                "unit": "worker_days",
                "contributor_count": abs_count,
                "exposure": 3400,
            })

        df = pd.DataFrame(records)

        # No ground truth heat-wave event occurred
        return df, None


