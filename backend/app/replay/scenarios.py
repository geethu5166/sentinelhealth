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

    @staticmethod
    def generate_air_quality_respiratory_surge_scenario(
        start_date: datetime,
        days: int = 45,
        seed: int = 501,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Deterministic scenario: particulate pollution (PM2.5) inversion episode
        corroborated by aggregate acute respiratory clinical contacts.
        Baseline: days 0-25 (PM2.5: 25-45 ug/m3, contacts: ~10/day).
        Episode: days 26-33 (PM2.5: 110-160 ug/m3, contacts: ~35/day).
        Post-event: days 34-45 (wind clearing, normal baselines).
        """
        np.random.seed(seed)
        records = []

        event_start_day = 26
        event_end_day = 33

        for d in range(days):
            current_day = start_date + timedelta(days=d)
            is_event = event_start_day <= d <= event_end_day

            # 1. PM2.5 Concentration (Threshold: 60.0 ug/m3)
            base_pm25 = 35.0 + 5.0 * math.sin(d / 5.0)
            noise_pm = float(np.random.normal(0, 4.0))
            pm25 = (base_pm25 + noise_pm) + (95.0 if is_event else 0.0)
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

            # 2. Named AQI (European AQI scale 0-100+, US AQI scale 0-500)
            # Preserved explicitly; NOT relabelled as Indian AQI
            eu_aqi = round(min(100.0, pm25 * 0.6 + float(np.random.normal(0, 2.0))), 1)
            us_aqi = round(min(500.0, pm25 * 1.6 + float(np.random.normal(0, 5.0))), 1)

            records.append({
                "timestamp": current_day,
                "metric_code": "aqi_eu",
                "signal_family": "environmental",
                "value": eu_aqi,
                "unit": "index_points",
                "contributor_count": None,
                "exposure": None,
                "geography_id": "DIST-DHANPUR",
                "aqi_system": "aqi_eu",
                "status": "valid",
            })
            records.append({
                "timestamp": current_day,
                "metric_code": "aqi_us",
                "signal_family": "environmental",
                "value": us_aqi,
                "unit": "index_points",
                "contributor_count": None,
                "exposure": None,
                "geography_id": "DIST-DHANPUR",
                "aqi_system": "aqi_us",
                "status": "valid",
            })

            # 3. Public-Health Tenant: Aggregate acute respiratory encounters with denominator
            base_resp = 10.0 + (2.0 if current_day.weekday() in [0, 1] else 0.0)
            resp_mult = 3.5 if is_event else 1.0
            resp_count = int(np.random.poisson(base_resp * resp_mult))

            records.append({
                "timestamp": current_day,
                "metric_code": "acute_respiratory_contacts",
                "signal_family": "clinical_service",
                "value": resp_count,
                "unit": "encounters",
                "contributor_count": resp_count,
                "exposure": 50000,  # 50,000 district catchment population
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

            # 4. Workforce Tenant: Explicitly coded respiratory sickness absence
            base_work_resp = 8.0
            work_mult = 3.0 if is_event else 1.0
            work_count = int(np.random.poisson(base_work_resp * work_mult))

            records.append({
                "timestamp": current_day,
                "metric_code": "respiratory_sickness_absence_days",
                "signal_family": "workforce",
                "value": work_count,
                "unit": "worker_days",
                "contributor_count": work_count,
                "exposure": 3200,  # workforce denominator
                "geography_id": "DIST-DHANPUR",
                "is_nonspecific": False,
                "status": "valid",
            })

        df = pd.DataFrame(records)

        reference_event = {
            "event_id": "REF-EVT-AIR-RESP-2026",
            "hazard": "air_quality_respiratory",
            "onset_at": (start_date + timedelta(days=event_start_day)).isoformat(),
            "end_at": (start_date + timedelta(days=event_end_day)).isoformat(),
            "severity": "warning",
            "earliest_useful_action_at": (start_date + timedelta(days=event_start_day - 1)).isoformat(),
            "evidence_basis": "Ground truth simulated particulate air pollution and acute respiratory surge",
        }

        return df, reference_event

    @staticmethod
    def generate_air_quality_stagnation_without_health_scenario(
        start_date: datetime,
        days: int = 45,
        seed: int = 601,
    ) -> Tuple[pd.DataFrame, Optional[Dict[str, Any]]]:
        """
        Pollution exceedance (PM2.5 >= 60 ug/m3) on days 26-30 without health surge.
        Demonstrates environmental exposure watch without clinical corroboration.
        """
        np.random.seed(seed)
        records = []

        inversion_start_day = 26
        inversion_end_day = 30

        for d in range(days):
            current_day = start_date + timedelta(days=d)
            is_inversion = inversion_start_day <= d <= inversion_end_day

            # PM2.5 elevated during inversion
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
                "contributor_count": None,
                "exposure": None,
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

            # Health contacts remain completely normal
            base_resp = 10.0
            resp_count = int(np.random.poisson(base_resp))

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

    @staticmethod
    def generate_respiratory_outbreak_without_pollution_scenario(
        start_date: datetime,
        days: int = 45,
        seed: int = 701,
    ) -> Tuple[pd.DataFrame, Optional[Dict[str, Any]]]:
        """
        Clinical respiratory surge on days 22-26 without particulate pollution.
        Clean air (PM2.5 ~25 ug/m3).
        Demonstrates uncorroborated health anomaly advisory.
        """
        np.random.seed(seed)
        records = []

        outbreak_start_day = 22
        outbreak_end_day = 26

        for d in range(days):
            current_day = start_date + timedelta(days=d)
            is_outbreak = outbreak_start_day <= d <= outbreak_end_day

            # PM2.5 clean and normal (20-30 ug/m3, far below 60 ug/m3)
            pm25 = round(25.0 + float(np.random.normal(0, 3.0)), 1)
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

            # Clinical surge
            base_resp = 10.0
            resp_mult = 3.2 if is_outbreak else 1.0
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
        return df, None

    @staticmethod
    def generate_air_quality_null_scenario(
        start_date: datetime,
        days: int = 45,
        seed: int = 801,
    ) -> Tuple[pd.DataFrame, Optional[Dict[str, Any]]]:
        """Null hypothesis scenario: clean air and stable baseline health."""
        np.random.seed(seed)
        records = []

        for d in range(days):
            current_day = start_date + timedelta(days=d)
            pm25 = round(28.0 + float(np.random.normal(0, 3.0)), 1)
            resp_count = int(np.random.poisson(10.0))

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
                "value": resp_count,
                "unit": "encounters",
                "exposure": 50000,
                "geography_id": "DIST-DHANPUR",
                "status": "valid",
            })

        df = pd.DataFrame(records)
        return df, None



