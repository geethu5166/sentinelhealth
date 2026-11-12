"""One-sided CUSUM detector for sustained residual elevation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class CusumScore:
    standardised_residual: float
    cusum_value: float
    decision_interval: float
    is_anomaly: bool
    severity_level: str
    details: Dict[str, Any]


class OneSidedCUSUMDetector:
    """
    Tabular one-sided CUSUM on standardised residuals.

    S_t = max(0, S_{t-1} + r_t - k)
    Alarm when S_t > h

    Defaults follow common SPC practice for upper-tail health surveillance.
    """

    def __init__(self, slack_k: float = 0.5, decision_interval_h: float = 4.0):
        if slack_k <= 0:
            raise ValueError("slack_k must be positive")
        if decision_interval_h <= 0:
            raise ValueError("decision_interval_h must be positive")
        self.k = slack_k
        self.h = decision_interval_h
        self._s = 0.0
        self._t = 0

    def reset(self) -> None:
        self._s = 0.0
        self._t = 0

    def update(self, standardised_residual: float) -> CusumScore:
        self._t += 1
        r = float(standardised_residual)
        self._s = max(0.0, self._s + r - self.k)
        is_anomaly = self._s > self.h
        # Map exceedance magnitude to screening severity bands
        exceed = self._s - self.h
        if not is_anomaly:
            severity = "none"
        elif exceed < 1.0:
            severity = "watch"
        elif exceed < 2.5:
            severity = "warning"
        else:
            severity = "critical"

        return CusumScore(
            standardised_residual=round(r, 4),
            cusum_value=round(self._s, 4),
            decision_interval=self.h,
            is_anomaly=is_anomaly,
            severity_level=severity,
            details={
                "algorithm": "one-sided-CUSUM",
                "k": self.k,
                "h": self.h,
                "t": self._t,
                "evidence_label": "screening",
            },
        )

    def score_series(self, residuals: List[float]) -> List[CusumScore]:
        self.reset()
        return [self.update(r) for r in residuals]
