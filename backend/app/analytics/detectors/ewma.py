"""Standard signed-residual EWMA detector with upper-tail monitoring.

Mathematical formulation adheres to:
NIST/SEMATECH e-Handbook of Statistical Methods §6.3.2.4 (EWMA Control Charts)
https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc324.htm

Standard formulation:
    r_t = (y_t - \\hat{\\mu}_t) / \\sqrt{\\hat{V}_t}
    E_t = \\lambda r_t + (1 - \\lambda) E_{t-1}

where:
    - y_t is observed aggregate count / rate
    - \\hat{\\mu}_t is baseline-estimated expected value
    - \\hat{V}_t is baseline-estimated variance (e.g. \\hat{\\mu}_t for Poisson)
    - r_t is the signed standardised residual (in-control mean \\mu_0 = 0, \\sigma_0 = 1)
    - \\lambda \\in (0, 1] is the smoothing weight
    - E_0 = 0 (initialisation in-control)
    - Time-varying Upper Control Limit (UCL):
        \\sigma_{E,t} = \\sqrt{\\frac{\\lambda}{2-\\lambda} \\left[1 - (1-\\lambda)^{2t}\\right]}
        \\text{UCL}_t = L \\cdot \\sigma_{E,t}

Only the upper control limit is evaluated (E_t > UCL_t) to detect rising health/workforce risks.
Negative residuals are preserved in the EWMA calculation to properly represent periods below baseline,
preventing spurious alarms caused by isolated spikes following extended below-average periods.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class AnomalyScore:
    observed: float
    expected: float
    excess: float
    standardised_residual: float
    ewma_value: float
    ewma_threshold: float
    is_anomaly: bool
    is_sustained: bool
    severity_level: str  # none, advisory, watch, warning, critical
    details: Dict[str, Any]


class OneSidedEWMADetector:
    """
    Standard signed-residual EWMA detector with upper-tail monitoring.
    
    Adheres to NIST/SEMATECH §6.3.2.4:
    - Standardised residuals are smoothed without pre-clipping:
      E_t = lambda * r_t + (1 - lambda) * E_{t-1}
    - Time-varying upper control limit (UCL) accounts for early-run variance reduction:
      UCL_t = L * sqrt((lambda / (2 - lambda)) * (1 - (1 - lambda)^(2t)))
    - Only the upper tail (E_t > UCL_t) is monitored for rising disease or injury incidence.
    """

    def __init__(
        self,
        smoothing_factor: float = 0.3,
        control_limit_sigma: float = 2.5,
        min_observations: int = 7,
        use_positive_part_variant: bool = False,
    ):
        """
        Parameters
        ----------
        smoothing_factor : float
            Weight assigned to the most recent observation (lambda). Default 0.3.
        control_limit_sigma : float
            Multiplier (L) for the asymptotic standard error. Default 2.5.
        min_observations : int
            Minimum number of observations before sustained anomaly flags are considered reliable.
        use_positive_part_variant : bool
            If True, clips negative residuals to 0 (non-standard variant; requires independent calibration).
            Default False (standard signed EWMA per NIST).
        """
        if not 0.0 < smoothing_factor <= 1.0:
            raise ValueError(f"smoothing_factor must be in (0, 1], got {smoothing_factor}")
        if control_limit_sigma <= 0.0:
            raise ValueError(f"control_limit_sigma must be positive, got {control_limit_sigma}")

        self.smoothing_factor = smoothing_factor  # lambda
        self.control_limit_sigma = control_limit_sigma  # L
        self.min_observations = min_observations
        self.use_positive_part_variant = use_positive_part_variant
        self.version = "1.1.0-nist-signed"

    def compute_anomaly(
        self,
        observed: float,
        expected: float,
        standard_error: float,
        historical_residuals: Optional[List[float]] = None,
        step_number: Optional[int] = None,
    ) -> AnomalyScore:
        """
        Calculates standardized residual and one-sided EWMA value.

        Parameters
        ----------
        observed : float
            Current observed aggregate signal value (y_t).
        expected : float
            Baseline expected value (\\hat{\\mu}_t).
        standard_error : float
            Estimated standard error \\sqrt{\\hat{V}_t}.
        historical_residuals : Optional[List[float]]
            Chronological sequence of prior standardised residuals [r_1, r_2, ..., r_{t-1}].
        step_number : Optional[int]
            Observation index t (1-indexed) for exact time-varying UCL computation.
            If omitted, len(historical_residuals) + 1 is used.

        Returns
        -------
        AnomalyScore
            Comprehensive anomaly metrics including EWMA value, UCL threshold, and severity.
        """
        excess = observed - expected
        # Minimum SE floor of 0.25 to prevent numerical singularity on near-zero baseline rates
        se = max(0.25, standard_error)
        std_residual = excess / se

        residuals = list(historical_residuals or []) + [std_residual]
        t = step_number or len(residuals)

        # Standard signed-input EWMA smoothing:
        # E_t = lambda * r_t + (1 - lambda) * E_{t-1}
        # Initialisation: E_0 = 0.0 (in-control mean)
        ewma = 0.0
        for r in residuals:
            if self.use_positive_part_variant:
                # Explicit positive-part variant (floor at zero)
                ewma = max(0.0, self.smoothing_factor * r + (1.0 - self.smoothing_factor) * ewma)
            else:
                # Standard NIST signed smoothing
                ewma = self.smoothing_factor * r + (1.0 - self.smoothing_factor) * ewma

        # Exact time-varying Upper Control Limit (NIST §6.3.2.4 equation):
        # sigma_{E, t} = sqrt((lambda / (2 - lambda)) * (1 - (1 - lambda)^(2t)))
        # UCL_t = L * sigma_{E, t}
        lam = self.smoothing_factor
        asymptotic_var_factor = lam / (2.0 - lam)
        finite_sample_correction = 1.0 - math.pow(1.0 - lam, 2 * max(1, t))
        sigma_ewma_t = math.sqrt(asymptotic_var_factor * finite_sample_correction)
        threshold = self.control_limit_sigma * sigma_ewma_t

        # Detection logic:
        # 1. Immediate outlier spike: std_residual > 3.0
        # 2. Sustained upward accumulation: ewma > threshold (upper control limit breached)
        is_sustained = ewma > threshold and t >= min(3, self.min_observations)
        is_anomaly = (std_residual > 3.0) or is_sustained

        # Graduated public-health severity scale based on upper control limit ratio
        severity = "none"
        if ewma > threshold * 1.8 or std_residual > 4.5:
            severity = "critical"
        elif ewma > threshold * 1.3 or std_residual > 3.5:
            severity = "warning"
        elif is_sustained or ewma > threshold or std_residual > 2.5:
            severity = "watch"
        elif std_residual > 1.8 or ewma > threshold * 0.7:
            severity = "advisory"

        return AnomalyScore(
            observed=round(observed, 4),
            expected=round(expected, 4),
            excess=round(excess, 4),
            standardised_residual=round(std_residual, 4),
            ewma_value=round(ewma, 4),
            ewma_threshold=round(threshold, 4),
            is_anomaly=is_anomaly,
            is_sustained=is_sustained,
            severity_level=severity,
            details={
                "smoothing_factor": self.smoothing_factor,
                "control_limit_sigma": self.control_limit_sigma,
                "history_length": len(residuals),
                "step_number": t,
                "sigma_ewma_t": round(sigma_ewma_t, 4),
                "detector_version": self.version,
                "algorithm": "NIST-signed-EWMA" if not self.use_positive_part_variant else "positive-part-variant",
            },
        )
