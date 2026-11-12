"""Unit tests for ensemble baseline selection and CUSUM detector."""

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from app.analytics.baselines.ensemble import EnsembleBaselineSelector, SeasonalMovingAverageBaseline
from app.analytics.detectors.cusum import OneSidedCUSUMDetector


def _series(days: int = 45, base: float = 34.0) -> pd.DataFrame:
    start = datetime(2026, 4, 1, tzinfo=timezone.utc)
    rows = []
    for d in range(days):
        t = start + timedelta(days=d)
        val = base + (2.5 if t.weekday() >= 5 else 0.0) + (d % 7) * 0.35
        rows.append({"timestamp": t, "value": float(val), "exposure": 1.0})
    return pd.DataFrame(rows)


def test_seasonal_ema_predicts_positive():
    df = _series()
    model = SeasonalMovingAverageBaseline(span=14, min_samples=14)
    target = df["timestamp"].max().to_pydatetime() + timedelta(days=1)
    pred = model.fit_predict(df, target, current_exposure=1.0)
    assert pred.expected_value > 0
    assert pred.model_type == "seasonal_ema"
    assert pred.diagnostics.get("evidence_label") == "screening"


def test_ensemble_selects_a_candidate():
    df = _series(days=50)
    selector = EnsembleBaselineSelector(holdout_days=7)
    target = df["timestamp"].max().to_pydatetime() + timedelta(days=1)
    result = selector.fit_predict(df, target, current_exposure=1.0)
    assert result.selected.expected_value > 0
    assert len(result.candidates) >= 3
    assert result.selection_score >= 0
    assert result.selected.diagnostics.get("ensemble_selected") is True


def test_cusum_alarms_on_sustained_elevation():
    det = OneSidedCUSUMDetector(slack_k=0.5, decision_interval_h=4.0)
    scores = det.score_series([0.1, 0.2, 2.5, 2.8, 3.0, 3.2, 3.5])
    assert scores[-1].is_anomaly is True
    assert scores[-1].cusum_value > 4.0
    assert scores[-1].details["evidence_label"] == "screening"


def test_cusum_stays_quiet_on_noise():
    det = OneSidedCUSUMDetector(slack_k=0.5, decision_interval_h=4.0)
    scores = det.score_series([0.1, -0.2, 0.3, 0.0, 0.4, -0.1, 0.2])
    assert all(not s.is_anomaly for s in scores)
