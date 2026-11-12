"""Ensemble baseline selection over realtime / historical series."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from app.analytics.baselines.models import (
    BaselinePrediction,
    NegativeBinomialBaseline,
    PoissonCountBaseline,
    QuasiPoissonBaseline,
    RecentHistoryBaseline,
)


@dataclass
class EnsembleResult:
    selected: BaselinePrediction
    candidates: List[BaselinePrediction]
    selection_metric: str
    selection_score: float


class SeasonalMovingAverageBaseline:
    """Seasonal (weekday) exponential moving average for continuous environmental series."""

    def __init__(self, span: int = 14, min_samples: int = 14):
        self.span = span
        self.min_samples = min_samples
        self.version = "1.0.0"

    def fit_predict(
        self,
        historical_series: pd.DataFrame,
        target_timestamp: datetime,
        current_exposure: Optional[float] = None,
    ) -> BaselinePrediction:
        hist = historical_series[historical_series["timestamp"] < target_timestamp].copy()
        if len(hist) < self.min_samples:
            return RecentHistoryBaseline().fit_predict(historical_series, target_timestamp, current_exposure)

        hist["weekday"] = pd.to_datetime(hist["timestamp"]).dt.day_of_week
        target_weekday = target_timestamp.weekday()
        matched = hist[hist["weekday"] == target_weekday].tail(self.span)
        if len(matched) < 3:
            matched = hist.tail(self.span)

        values = matched["value"].dropna().astype(float).values
        if len(values) == 0:
            return RecentHistoryBaseline().fit_predict(historical_series, target_timestamp, current_exposure)

        # EMA with more weight on recent seasonal matches
        alpha = 2.0 / (len(values) + 1.0)
        ema = float(values[0])
        for v in values[1:]:
            ema = alpha * float(v) + (1.0 - alpha) * ema

        residual_std = float(np.std(values - ema, ddof=1)) if len(values) > 1 else max(0.5, abs(ema) * 0.15)
        residual_std = max(residual_std, 0.1)
        return BaselinePrediction(
            expected_value=round(ema, 4),
            standard_error=round(residual_std, 4),
            prediction_interval_lower=round(ema - 1.96 * residual_std, 4),
            prediction_interval_upper=round(ema + 1.96 * residual_std, 4),
            model_type="seasonal_ema",
            model_version=self.version,
            diagnostics={
                "status": "ok",
                "evidence_label": "screening",
                "sample_size": len(values),
                "span": self.span,
            },
        )


class EnsembleBaselineSelector:
    """Holdout MAE selector across GLM + seasonal baselines for realtime training."""

    def __init__(self, holdout_days: int = 7):
        self.holdout_days = holdout_days
        self.candidates = [
            RecentHistoryBaseline(lookback_days=28, weekday_matching=True),
            PoissonCountBaseline(min_samples=14),
            NegativeBinomialBaseline(min_samples=21),
            QuasiPoissonBaseline(min_samples=21),
            SeasonalMovingAverageBaseline(span=14, min_samples=14),
        ]

    def _holdout_mae(
        self,
        model: Any,
        series: pd.DataFrame,
        current_exposure: Optional[float],
    ) -> Optional[float]:
        if len(series) < self.holdout_days + 10:
            return None
        cutoff = series["timestamp"].max() - timedelta(days=self.holdout_days)
        train = series[series["timestamp"] <= cutoff]
        test = series[series["timestamp"] > cutoff]
        if train.empty or test.empty:
            return None
        errors: List[float] = []
        for _, row in test.iterrows():
            pred = model.fit_predict(train, row["timestamp"].to_pydatetime(), current_exposure)
            errors.append(abs(float(row["value"]) - float(pred.expected_value)))
        return float(np.mean(errors)) if errors else None

    def fit_predict(
        self,
        historical_series: pd.DataFrame,
        target_timestamp: datetime,
        current_exposure: Optional[float] = None,
    ) -> EnsembleResult:
        scored: List[Tuple[BaselinePrediction, float]] = []
        for model in self.candidates:
            pred = model.fit_predict(historical_series, target_timestamp, current_exposure)
            mae = self._holdout_mae(model, historical_series, current_exposure)
            # Prefer lower MAE; fall back to AIC when available, else residual SE
            if mae is not None:
                score = mae
                metric = "holdout_mae"
            elif pred.diagnostics.get("aic") is not None:
                score = float(pred.diagnostics["aic"])
                metric = "aic"
            else:
                score = float(pred.standard_error)
                metric = "standard_error"
            pred.diagnostics = {
                **pred.diagnostics,
                "ensemble_score": round(score, 4),
                "ensemble_metric": metric,
            }
            scored.append((pred, score))

        scored.sort(key=lambda item: item[1])
        best_pred, best_score = scored[0]
        best_pred.diagnostics["ensemble_selected"] = True
        return EnsembleResult(
            selected=best_pred,
            candidates=[p for p, _ in scored],
            selection_metric=best_pred.diagnostics.get("ensemble_metric", "holdout_mae"),
            selection_score=float(best_score),
        )
