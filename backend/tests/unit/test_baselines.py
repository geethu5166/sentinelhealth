"""Unit tests for baseline models."""

from datetime import datetime, timedelta, timezone
import pandas as pd
import pytest

from app.analytics.baselines.models import (
    NegativeBinomialBaseline,
    PoissonCountBaseline,
    QuasiPoissonBaseline,
    RecentHistoryBaseline,
)


def _series(days: int = 40, base: float = 12.0, overdispersion: float = 1.0) -> pd.DataFrame:
    start = datetime(2026, 6, 1, tzinfo=timezone.utc)
    data = []
    for d in range(days):
        t = start + timedelta(days=d)
        # Mild weekday effect + controlled noise for overdispersed counts
        val = base + (3.0 if t.weekday() >= 5 else 0.0) + (d % 5) * overdispersion
        data.append({"timestamp": t, "value": float(val), "exposure": 1000})
    return pd.DataFrame(data)


def test_recent_history_lookahead_exclusion():
    start = datetime(2026, 6, 1, tzinfo=timezone.utc)
    data = []
    for d in range(20):
        t = start + timedelta(days=d)
        val = 100.0 if d == 15 else 10.0
        data.append({"timestamp": t, "value": val, "exposure": 1000})

    df = pd.DataFrame(data)
    model = RecentHistoryBaseline(lookback_days=14, weekday_matching=False)

    target_time = start + timedelta(days=15)
    pred = model.fit_predict(df, target_time)

    # Scored day value (100.0) MUST NOT contaminate the baseline
    assert pred.expected_value == pytest.approx(10.0, abs=1.0)
    assert pred.prediction_interval_upper < 50.0


def test_poisson_baseline_fit():
    df = _series(days=25, base=15.0)
    model = PoissonCountBaseline(min_samples=14)

    target_time = df["timestamp"].max() + timedelta(days=1)
    pred = model.fit_predict(df, target_time, current_exposure=1000)

    assert pred.expected_value > 0.0
    assert pred.prediction_interval_lower <= pred.expected_value <= pred.prediction_interval_upper


def test_negative_binomial_baseline_fit():
    df = _series(days=40, base=18.0, overdispersion=2.5)
    model = NegativeBinomialBaseline(min_samples=21)
    target_time = df["timestamp"].max() + timedelta(days=1)
    pred = model.fit_predict(df, target_time, current_exposure=1000)

    assert pred.expected_value > 0.0
    assert pred.model_type in {"negative_binomial_glm", "poisson_glm", "recent_history_weekday_matched", "recent_history"}
    assert pred.prediction_interval_lower <= pred.expected_value <= pred.prediction_interval_upper
    assert pred.diagnostics.get("evidence_label", "screening") == "screening" or "fallback" in str(pred.diagnostics)


def test_quasi_poisson_baseline_fit():
    df = _series(days=40, base=20.0, overdispersion=3.0)
    model = QuasiPoissonBaseline(min_samples=21)
    target_time = df["timestamp"].max() + timedelta(days=1)
    pred = model.fit_predict(df, target_time, current_exposure=1000)

    assert pred.expected_value > 0.0
    assert pred.model_type in {"quasi_poisson_glm", "recent_history_weekday_matched", "recent_history"}
    assert pred.prediction_interval_lower <= pred.expected_value <= pred.prediction_interval_upper
    if pred.model_type == "quasi_poisson_glm":
        assert pred.diagnostics["dispersion"] >= 1.0
        assert pred.diagnostics["evidence_label"] == "screening"

