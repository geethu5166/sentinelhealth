"""Unit tests for the standard signed-residual EWMA detector and variants."""

import pytest
from app.analytics.detectors.ewma import OneSidedEWMADetector


def test_ewma_signed_residual_smoothing():
    """Negative residuals must decrease the EWMA statistic in standard NIST mode."""
    detector = OneSidedEWMADetector(smoothing_factor=0.3, control_limit_sigma=2.5)

    # 1. Negative residual (observed < expected)
    score_low = detector.compute_anomaly(observed=5.0, expected=10.0, standard_error=2.0)
    assert score_low.standardised_residual == -2.5
    # EWMA = 0.3 * (-2.5) + 0.7 * 0 = -0.75
    assert score_low.ewma_value < 0.0
    assert not score_low.is_anomaly
    assert not score_low.is_sustained


def test_ewma_sustained_accumulation_triggers_ucl():
    """A sustained sequence of positive residuals breaches the upper control limit."""
    detector = OneSidedEWMADetector(smoothing_factor=0.3, control_limit_sigma=2.5, min_observations=3)

    hist = [2.0, 2.5, 3.0]
    score = detector.compute_anomaly(
        observed=20.0,
        expected=10.0,
        standard_error=2.0,
        historical_residuals=hist,
    )
    # Standard residual = (20 - 10) / 2 = 5.0
    assert score.standardised_residual == 5.0
    assert score.ewma_value > score.ewma_threshold
    assert score.is_anomaly
    assert score.is_sustained
    assert score.severity_level in ["watch", "warning", "critical"]


def test_ewma_time_varying_control_limit():
    """Exact UCL should widen as observation count increases towards asymptotic limit."""
    detector = OneSidedEWMADetector(smoothing_factor=0.3, control_limit_sigma=2.5)

    score_t1 = detector.compute_anomaly(observed=10.0, expected=10.0, standard_error=1.0, historical_residuals=[])
    score_t10 = detector.compute_anomaly(
        observed=10.0,
        expected=10.0,
        standard_error=1.0,
        historical_residuals=[0.0] * 9,
    )

    # UCL at t=1 is narrower than at t=10 due to finite-sample correction
    assert score_t1.ewma_threshold < score_t10.ewma_threshold
    assert score_t1.details["algorithm"] == "NIST-signed-EWMA"


def test_positive_part_variant_floors_at_zero():
    """When configured with use_positive_part_variant=True, negative residuals floor at zero."""
    detector = OneSidedEWMADetector(
        smoothing_factor=0.3,
        control_limit_sigma=2.5,
        use_positive_part_variant=True,
    )
    score = detector.compute_anomaly(observed=5.0, expected=10.0, standard_error=2.0)
    assert score.ewma_value == 0.0
    assert score.details["algorithm"] == "positive-part-variant"
