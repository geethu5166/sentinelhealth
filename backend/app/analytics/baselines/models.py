"""Interpretable baseline estimation models."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


@dataclass
class BaselinePrediction:
    expected_value: float
    standard_error: float
    prediction_interval_lower: float
    prediction_interval_upper: float
    model_type: str
    model_version: str
    diagnostics: Dict[str, Any]


class RecentHistoryBaseline:
    """
    Transparent recent-history and weekday-matched baseline for cold-start and robust comparison.
    Computes median or mean of historical matching weekdays within a lookback window (e.g. 28-90 days).
    """

    def __init__(self, lookback_days: int = 28, weekday_matching: bool = True):
        self.lookback_days = lookback_days
        self.weekday_matching = weekday_matching
        self.version = "1.0.0"

    def fit_predict(
        self,
        historical_series: pd.DataFrame,
        target_timestamp: datetime,
        exposure: Optional[float] = None,
    ) -> BaselinePrediction:
        """
        historical_series: DataFrame with columns ['timestamp', 'value', 'exposure']
        target_timestamp: the time point being scored (strictly excluded from history)
        """
        # Strictly exclude target and future data
        hist = historical_series[historical_series["timestamp"] < target_timestamp].copy()

        if len(hist) < 7:
            # Insufficient history
            return BaselinePrediction(
                expected_value=0.0,
                standard_error=0.0,
                prediction_interval_lower=0.0,
                prediction_interval_upper=0.0,
                model_type="recent_history",
                model_version=self.version,
                diagnostics={"status": "insufficient_history", "history_count": len(hist)},
            )

        hist["weekday"] = pd.to_datetime(hist["timestamp"]).dt.weekday
        target_weekday = target_timestamp.weekday()

        if self.weekday_matching:
            matched = hist[hist["weekday"] == target_weekday]
            if len(matched) < 3:
                # Fallback to all days in window
                matched = hist.tail(self.lookback_days)
        else:
            matched = hist.tail(self.lookback_days)

        values = matched["value"].dropna().astype(float).values

        if len(values) == 0:
            return BaselinePrediction(
                expected_value=0.0,
                standard_error=0.0,
                prediction_interval_lower=0.0,
                prediction_interval_upper=0.0,
                model_type="recent_history",
                model_version=self.version,
                diagnostics={"status": "no_valid_values"},
            )

        mean_val = float(np.mean(values))
        std_val = float(np.std(values, ddof=1)) if len(values) > 1 else max(0.5, mean_val * 0.2)

        # Poisson-like variance lower bound for count data
        std_val = max(std_val, math.sqrt(max(0.1, mean_val)))

        # Prediction interval (approx 95% using 1.96 standard deviations)
        lower_bound = max(0.0, mean_val - 1.96 * std_val)
        upper_bound = mean_val + 1.96 * std_val

        return BaselinePrediction(
            expected_value=round(mean_val, 4),
            standard_error=round(std_val, 4),
            prediction_interval_lower=round(lower_bound, 4),
            prediction_interval_upper=round(upper_bound, 4),
            model_type="recent_history_weekday_matched",
            model_version=self.version,
            diagnostics={
                "status": "ok",
                "sample_size": len(values),
                "lookback_days": self.lookback_days,
                "weekday_matched": self.weekday_matching,
            },
        )


class PoissonCountBaseline:
    """
    Poisson regression baseline with optional log exposure offset.
    Suitable for count data (e.g. daily service visits or sick worker days).
    """

    def __init__(self, min_samples: int = 14):
        self.min_samples = min_samples
        self.version = "1.0.0"

    def fit_predict(
        self,
        historical_series: pd.DataFrame,
        target_timestamp: datetime,
        current_exposure: Optional[float] = None,
    ) -> BaselinePrediction:
        import statsmodels.api as sm

        hist = historical_series[historical_series["timestamp"] < target_timestamp].copy()
        if len(hist) < self.min_samples:
            # Fall back to recent history
            fallback = RecentHistoryBaseline()
            return fallback.fit_predict(historical_series, target_timestamp, current_exposure)

        hist["weekday"] = pd.to_datetime(hist["timestamp"]).dt.weekday
        # Simple weekday categorical predictors
        X = pd.get_dummies(hist["weekday"], drop_first=True, dtype=float)
        X = sm.add_constant(X)
        y = hist["value"].astype(float).values

        exposure = hist.get("exposure")
        offset = np.log(exposure.astype(float).values) if exposure is not None and not exposure.isna().all() else None

        try:
            model = sm.GLM(y, X, family=sm.families.Poisson(), offset=offset)
            res = model.fit(disp=False)

            # Predict for target day
            target_weekday = target_timestamp.weekday()
            target_x = pd.DataFrame(0.0, index=[0], columns=X.columns)
            target_x["const"] = 1.0
            if target_weekday in target_x.columns:
                target_x[target_weekday] = 1.0

            target_offset = math.log(current_exposure) if current_exposure and current_exposure > 0 else None
            pred = res.predict(target_x, offset=target_offset)[0]

            # Poisson variance equals mean
            std_err = math.sqrt(max(0.1, pred))
            lower_bound = max(0.0, pred - 1.96 * std_err)
            upper_bound = pred + 1.96 * std_err

            return BaselinePrediction(
                expected_value=round(float(pred), 4),
                standard_error=round(float(std_err), 4),
                prediction_interval_lower=round(float(lower_bound), 4),
                prediction_interval_upper=round(float(upper_bound), 4),
                model_type="poisson_glm",
                model_version=self.version,
                diagnostics={
                    "status": "ok",
                    "aic": round(float(res.aic), 2),
                    "deviance": round(float(res.deviance), 2),
                    "sample_size": len(hist),
                },
            )
        except Exception as e:
            # Fallback to recent history on numerical convergence issues
            fallback = RecentHistoryBaseline()
            pred = fallback.fit_predict(historical_series, target_timestamp, current_exposure)
            pred.diagnostics["poisson_fallback_reason"] = str(e)
            return pred

