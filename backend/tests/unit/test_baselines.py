"""Unit tests for baseline models."""

from datetime import datetime, timedelta, timezone
import pandas as pd
import pytest

from app.analytics.baselines.models import PoissonCountBaseline, RecentHistoryBaseline


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
    start = datetime(2026, 6, 1, tzinfo=timezone.utc)
    data = []
    for d in range(25):
        t = start + timedelta(days=d)
        data.append({"timestamp": t, "value": 14.0 + float(d % 3), "exposure": 1000})

    model = PoissonCountBaseline(min_samples=14)
    df = pd.DataFrame(data)

    target_time = start + timedelta(days=25)
    pred = model.fit_predict(df, target_time, current_exposure=1000)

    assert pred.expected_value > 0.0
    assert pred.prediction_interval_lower <= pred.expected_value <= pred.prediction_interval_upper


def test_poisson_baseline_all_zero_series():
    """Verify that PoissonCountBaseline gracefully handles all-zero historical series without crashing."""
    start = datetime(2026, 6, 1, tzinfo=timezone.utc)
    data = []
    for d in range(25):
        t = start + timedelta(days=d)
        data.append({"timestamp": t, "value": 0.0, "exposure": 1000})

    model = PoissonCountBaseline(min_samples=14)
    df = pd.DataFrame(data)

    target_time = start + timedelta(days=25)
    pred = model.fit_predict(df, target_time, current_exposure=1000)

    assert pred.expected_value == 0.0
    assert pred.model_type in ["poisson_all_zero", "recent_history"]
    assert pred.diagnostics["status"] in ["all_zeros_observed", "ok"]


