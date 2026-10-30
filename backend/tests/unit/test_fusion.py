"""Unit tests for evidence fusion policy."""

from datetime import datetime, timezone
from app.analytics.fusion.policy import EvidenceFusionEngine, EvidenceItem


def test_fusion_corroborated_warning():
    engine = EvidenceFusionEngine()
    now = datetime.now(timezone.utc)

    # 1. Environmental exceedance
    ev_env = EvidenceItem(
        signal_family="environmental",
        metric_code="apparent_temperature",
        observed=41.5,
        expected=32.0,
        excess=9.5,
        standardised_residual=3.2,
        ewma_value=2.8,
        is_anomaly=True,
        source_freshness_minutes=15,
        is_fresh=True,
        is_stale=False,
        data_label="synthetic",
        geography_id="DIST-1",
        timestamp=now,
    )

    # 2. Workforce anomaly
    ev_work = EvidenceItem(
        signal_family="workforce",
        metric_code="sickness_absence_worker_days",
        observed=60.0,
        expected=20.0,
        excess=40.0,
        standardised_residual=3.8,
        ewma_value=3.4,
        is_anomaly=True,
        source_freshness_minutes=60,
        is_fresh=True,
        is_stale=False,
        data_label="synthetic",
        geography_id="DIST-1",
        timestamp=now,
    )

    decision = engine.evaluate(
        hazard="heat_illness",
        evidences=[ev_env, ev_work],
        environmental_thresholds={"apparent_temperature": 39.0},
    )

    assert decision.should_alert is True
    assert decision.evidence_class == "corroborated_health_warning"
    assert decision.severity in ["warning", "critical"]
    assert decision.evidence_score >= 60.0


def test_fusion_environmental_watch_only():
    engine = EvidenceFusionEngine()
    now = datetime.now(timezone.utc)

    # High heat, but health signals normal
    ev_env = EvidenceItem(
        signal_family="environmental",
        metric_code="apparent_temperature",
        observed=42.0,
        expected=32.0,
        excess=10.0,
        standardised_residual=3.5,
        ewma_value=3.0,
        is_anomaly=True,
        source_freshness_minutes=15,
        is_fresh=True,
        is_stale=False,
        data_label="synthetic",
        geography_id="DIST-1",
        timestamp=now,
    )
    ev_health = EvidenceItem(
        signal_family="clinical_service",
        metric_code="heat_exhaustion_contacts",
        observed=11.0,
        expected=12.0,
        excess=-1.0,
        standardised_residual=-0.3,
        ewma_value=0.0,
        is_anomaly=False,
        source_freshness_minutes=30,
        is_fresh=True,
        is_stale=False,
        data_label="synthetic",
        geography_id="DIST-1",
        timestamp=now,
    )

    decision = engine.evaluate(
        hazard="heat_illness",
        evidences=[ev_env, ev_health],
        environmental_thresholds={"apparent_temperature": 39.0},
    )

    assert decision.should_alert is True
    assert decision.evidence_class == "environmental_watch"
    assert decision.severity == "watch"

