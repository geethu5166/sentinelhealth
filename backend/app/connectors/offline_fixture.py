"""
Offline Synthetic Fixture Connector for Air-Gapped Simulation & Validation.

Scientific Framework & Operational Caveats:
------------------------------------------
1. Synthetic Data & Surveillance Ethics:
   This connector loads deterministic, synthetic signal records and scenario fixtures for
   air-gapped evaluation, replay benchmarking, and continuous integration.
   All records are strictly aggregate population or environmental screening measures.
   No Personally Identifiable Information (PII) or individual clinical diagnostics are contained.
   All fixture records are explicitly marked with data_label='synthetic'.

2. Wet-Bulb Temperature (Tw) != Wet-Bulb Globe Temperature (WBGT):
   - Psychrometric / Natural Wet-Bulb Temperature (Tw) models thermodynamic evaporative cooling limits.
   - Wet-Bulb Globe Temperature (WBGT) [ISO 7243 / OSHA / ACGIH]:
       Outdoor: WBGT = 0.7 * Tnw + 0.2 * Tg + 0.1 * Ta
       Indoor:  WBGT = 0.7 * Tnw + 0.3 * Tg
   - SCIENTIFIC LIMITATION: WBGT CANNOT be calculated from ambient dry-bulb temperature and relative
     humidity alone. It physically requires radiant heat flux (black-globe temperature Tg) and air velocity (v).
     Any proxy derived purely from dry-bulb temperature and humidity is strictly an uncalibrated shaded
     screening proxy. In unshaded operational zones or near industrial furnaces, true thermal strain
     may significantly exceed the screening proxy.

3. Heat Index (HI) Assumptions:
   - Rothfusz / NOAA Heat Index assumes shaded exposure and light wind (~5 knots / 2.5 m/s).
   - Direct radiant sunlight increases effective thermal burden by up to 8°C (15°F).
   - Personal Protective Equipment (PPE) such as vapor-barrier suits drastically accelerates heat strain.

4. Multi-Tiered Exposure Screening Features:
   - Hourly Granularity: Retains hourly resolution to model diurnal exposure trajectories.
   - Shift-Level Maximums: Extracts shift-peak heat index or WBGT proxy and duration (hours) above threshold
     for morning, afternoon, and night operational shifts. Shift-peak exposure metrics drive rapid
     workplace interventions (e.g. mandatory hydration pauses, cooling station access, work-rest cycles).
   - Daily Summary Metrics: Computes daily maximums, total exposure hours, and consecutive hours >= threshold
     (e.g., >= 38°C or >= 40°C). Consecutive hours without thermal respite severely impair core thermoregulation.
   - Rolling 7-Day Trend: Strictly designated for multi-day background context (tracking cumulative
     fatigue, community vulnerability, and acclimatization deficits). It MUST NOT be used as the primary
     triggering mechanism for acute heat stress warnings, which require shift-peak and consecutive hours
     for rapid exertional heat illness prevention.
"""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
import pandas as pd

from app.connectors.base import BaseConnector, NormalizedRecord
from app.connectors.heat_screening import (
    DEFAULT_HEAT_INDEX_WARNING,
    DEFAULT_WBGT_SCREENING_THRESHOLD,
    extract_all_heat_screening_features,
)


class OfflineFixtureConnector(BaseConnector):
    """
    Loads pre-generated synthetic fixture records from local files.
    Enables reproducible demo and validation without external network dependencies.
    All data is strictly synthetic and aggregate, with zero PII.
    """

    async def test_connection(self) -> bool:
        file_path = self.configuration.get("file_path", "")
        return os.path.exists(file_path)

    async def fetch(self, start_time: datetime, end_time: datetime) -> List[NormalizedRecord]:
        file_path = self.configuration.get("file_path", "")
        if not os.path.exists(file_path):
            return []

        extract_screening_features = self.configuration.get("extract_features", False)
        heat_threshold = float(self.configuration.get("heat_threshold", DEFAULT_HEAT_INDEX_WARNING))
        wbgt_threshold = float(self.configuration.get("wbgt_threshold", DEFAULT_WBGT_SCREENING_THRESHOLD))

        records: List[NormalizedRecord] = []
        df = pd.read_csv(file_path)

        for _, row in df.iterrows():
            p_start = pd.to_datetime(row["period_start"]).to_pydatetime()
            p_end = pd.to_datetime(row["period_end"]).to_pydatetime()

            # Ensure UTC timezone
            if p_start.tzinfo is None:
                p_start = p_start.replace(tzinfo=timezone.utc)
            if p_end.tzinfo is None:
                p_end = p_end.replace(tzinfo=timezone.utc)

            # Filter by time range if requested
            if start_time and p_end < start_time:
                continue
            if end_time and p_start > end_time:
                continue

            obs_at = pd.to_datetime(row.get("observed_at", row["period_end"])).to_pydatetime()
            if obs_at.tzinfo is None:
                obs_at = obs_at.replace(tzinfo=timezone.utc)

            src_avail = pd.to_datetime(row.get("source_available_at", obs_at)).to_pydatetime()
            if src_avail.tzinfo is None:
                src_avail = src_avail.replace(tzinfo=timezone.utc)

            num = float(row["numerator"]) if pd.notna(row.get("numerator")) else None
            den = float(row["denominator"]) if pd.notna(row.get("denominator")) else None
            contrib = int(row["contributor_count"]) if pd.notna(row.get("contributor_count")) else None

            # Enforce synthetic label and aggregate disclosure protection
            data_label = str(row.get("data_label", "synthetic"))
            if data_label != "real":
                data_label = "synthetic"

            rec = NormalizedRecord(
                source_record_id=str(row.get("source_record_id", f"rec_{len(records)}")),
                metric_code=str(row["metric_code"]),
                signal_family=str(row["signal_family"]),
                value=float(row["value"]),
                unit=str(row["unit"]),
                numerator=num,
                denominator=den,
                denominator_unit=str(row["denominator_unit"]) if pd.notna(row.get("denominator_unit")) else None,
                contributor_count=contrib,
                contributor_definition=str(row["contributor_definition"]) if pd.notna(row.get("contributor_definition")) else None,
                period_start=p_start,
                period_end=p_end,
                observed_at=obs_at,
                source_available_at=src_avail,
                geography_id=str(row["geography_id"]) if pd.notna(row.get("geography_id")) else None,
                workplace_id=str(row["workplace_id"]) if pd.notna(row.get("workplace_id")) else None,
                location_basis=str(row.get("location_basis", "model_grid")),
                location_confidence=str(row.get("location_confidence", "estimated")),
                data_label=data_label,
                quality_flags={
                    "is_synthetic_fixture": True,
                    "screening_context_only": True,
                },
                completeness=float(row["completeness"]) if pd.notna(row.get("completeness")) else 1.0,
                provenance=str(row.get("provenance", "offline_synthetic_fixture")),
            )
            records.append(rec)

        # Optionally extract multi-tier screening features if hourly environmental records are present
        if extract_screening_features:
            env_hourly = [r for r in records if r.signal_family == "environmental"]
            if env_hourly:
                screening_features = extract_all_heat_screening_features(
                    hourly_records=env_hourly,
                    heat_threshold=heat_threshold,
                    wbgt_threshold=wbgt_threshold,
                    data_label="synthetic",
                    provenance="offline_synthetic_fixture",
                )
                records.extend(screening_features)

        return records
