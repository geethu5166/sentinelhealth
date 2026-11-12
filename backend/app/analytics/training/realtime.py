"""Realtime Open-Meteo ingest + ensemble baseline training."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
import pandas as pd

from app.analytics.baselines.ensemble import EnsembleBaselineSelector, EnsembleResult
from app.analytics.detectors.cusum import OneSidedCUSUMDetector
from app.analytics.detectors.ewma import OneSidedEWMADetector
from app.connectors.heat_screening import calculate_heat_index


OPEN_METEO_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"


@dataclass
class RealtimeTrainReport:
    latitude: float
    longitude: float
    metric_code: str
    sample_size: int
    trained_at: str
    selected_model: str
    expected_value: float
    standard_error: float
    selection_metric: str
    selection_score: float
    ewma_anomaly: bool
    cusum_anomaly: bool
    latest_observed: float
    candidate_models: List[Dict[str, Any]]
    provenance: str
    evidence_label: str = "screening"


async def fetch_open_meteo_hourly(
    latitude: float,
    longitude: float,
    lookback_days: int = 60,
) -> pd.DataFrame:
    """Pull realtime + recent historical hourly weather for training."""
    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(days=lookback_days)

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m,relative_humidity_2m",
        "timezone": "UTC",
        "start_date": start.date().isoformat(),
        "end_date": end.date().isoformat(),
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        # Prefer archive for multi-week history; fall back to forecast API (past_days).
        try:
            res = await client.get(OPEN_METEO_ARCHIVE, params=params)
            res.raise_for_status()
            payload = res.json()
        except Exception:
            forecast_params = {
                "latitude": latitude,
                "longitude": longitude,
                "hourly": "temperature_2m,relative_humidity_2m",
                "timezone": "UTC",
                "past_days": min(lookback_days, 92),
                "forecast_days": 1,
            }
            res = await client.get(OPEN_METEO_FORECAST, params=forecast_params)
            res.raise_for_status()
            payload = res.json()

    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    temps = hourly.get("temperature_2m") or []
    rhs = hourly.get("relative_humidity_2m") or []

    rows: List[Dict[str, Any]] = []
    for i, ts in enumerate(times):
        if i >= len(temps) or temps[i] is None:
            continue
        ta = float(temps[i])
        rh = float(rhs[i]) if i < len(rhs) and rhs[i] is not None else 50.0
        hi = calculate_heat_index(ta, rh)
        rows.append(
            {
                "timestamp": datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc),
                "value": float(hi if hi is not None else ta),
                "exposure": 1.0,
                "dry_bulb_c": ta,
                "relative_humidity": rh,
            }
        )

    if not rows:
        raise RuntimeError("Open-Meteo returned no hourly observations for training")

    df = pd.DataFrame(rows).sort_values("timestamp")
    # Daily max heat-index for stable daily baselines / detectors
    df["day"] = pd.to_datetime(df["timestamp"]).dt.floor("D")
    daily = (
        df.groupby("day", as_index=False)
        .agg(value=("value", "max"), exposure=("exposure", "sum"))
        .rename(columns={"day": "timestamp"})
    )
    daily["timestamp"] = pd.to_datetime(daily["timestamp"], utc=True)
    return daily


async def train_realtime_heat_baselines(
    latitude: float = 21.1458,
    longitude: float = 79.0882,
    lookback_days: int = 60,
) -> RealtimeTrainReport:
    """Fetch live Open-Meteo history and train an ensemble screening baseline."""
    series = await fetch_open_meteo_hourly(latitude, longitude, lookback_days=lookback_days)
    target = series["timestamp"].max().to_pydatetime()
    if target.tzinfo is None:
        target = target.replace(tzinfo=timezone.utc)

    selector = EnsembleBaselineSelector(holdout_days=7)
    result: EnsembleResult = selector.fit_predict(series, target + timedelta(days=1), current_exposure=1.0)

    # Score the latest day residual with EWMA + CUSUM for dual-detector confirmation
    hist = series.iloc[:-1] if len(series) > 1 else series
    latest_obs = float(series.iloc[-1]["value"])
    expected = float(result.selected.expected_value)
    se = max(0.1, float(result.selected.standard_error))
    residual = (latest_obs - expected) / se

    prior_residuals: List[float] = []
    for _, row in hist.tail(21).iterrows():
        prior_residuals.append((float(row["value"]) - expected) / se)

    ewma = OneSidedEWMADetector(smoothing_factor=0.25, control_limit_sigma=2.5)
    ewma_score = ewma.compute_anomaly(
        observed=latest_obs,
        expected=expected,
        standard_error=se,
        historical_residuals=prior_residuals,
    )

    cusum = OneSidedCUSUMDetector(slack_k=0.5, decision_interval_h=4.0)
    for r in prior_residuals:
        cusum.update(r)
    cusum_score = cusum.update(residual)

    return RealtimeTrainReport(
        latitude=latitude,
        longitude=longitude,
        metric_code="heat_index_daily_max",
        sample_size=int(len(series)),
        trained_at=datetime.now(timezone.utc).isoformat(),
        selected_model=result.selected.model_type,
        expected_value=float(result.selected.expected_value),
        standard_error=float(result.selected.standard_error),
        selection_metric=result.selection_metric,
        selection_score=float(result.selection_score),
        ewma_anomaly=bool(ewma_score.is_anomaly),
        cusum_anomaly=bool(cusum_score.is_anomaly),
        latest_observed=latest_obs,
        candidate_models=[
            {
                "model_type": c.model_type,
                "expected_value": c.expected_value,
                "standard_error": c.standard_error,
                "diagnostics": c.diagnostics,
            }
            for c in result.candidates
        ],
        provenance="Open-Meteo archive/forecast · ensemble screening baselines",
        evidence_label="screening",
    )


def report_to_dict(report: RealtimeTrainReport) -> Dict[str, Any]:
    return asdict(report)
