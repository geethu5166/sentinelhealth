"""Deterministic evidence fusion engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional


@dataclass
class EvidenceItem:
    signal_family: str
    metric_code: str
    observed: float
    expected: float
    excess: float
    standardised_residual: float
    ewma_value: float
    is_anomaly: bool
    source_freshness_minutes: int
    is_fresh: bool
    is_stale: bool
    data_label: str
    geography_id: str
    timestamp: datetime


ContributingEvidence = EvidenceItem


@dataclass
class FusionDecision:
    hazard: str
    evidence_class: str
    severity: str
    evidence_score: float  # 0-100
    should_alert: bool = True
    reasons: List[str] = field(default_factory=list)
    contributing_evidences: List[EvidenceItem] = field(default_factory=list)
    missing_families: List[str] = field(default_factory=list)
    policy_version: str = "0.1.0"


class EvidenceFusionEngine:
    """
    Deterministic rule engine that fuses multi-signal evidence into actionable warnings.
    Ref: Spec requirement on evidence fusion without claiming correlation proves causation.
    """

    def __init__(self, policy_version: str = "0.1.0"):
        self.policy_version = policy_version

    def evaluate(
        self,
        hazard: str,
        evidences: List[EvidenceItem],
        environmental_thresholds: Dict[str, float],
        is_urgent_safety_trigger: bool = False,
    ) -> FusionDecision:
        """
        Executes fusion rules against current evidence set.
        """
        reasons = []

        # Urgent safety trigger bypasses routine corroboration
        if is_urgent_safety_trigger:
            return FusionDecision(
                hazard=hazard,
                evidence_class="safety_escalation",
                severity="critical",
                evidence_score=95.0,
                should_alert=True,
                reasons=["Urgent trusted workplace safety trigger received; routine corroboration bypassed."],
                contributing_evidences=evidences,
                missing_families=[],
                policy_version=self.policy_version,
            )

        # Partition by signal family
        by_family: Dict[str, List[EvidenceItem]] = {}
        for ev in evidences:
            by_family.setdefault(ev.signal_family, []).append(ev)

        has_env = "environmental" in by_family
        has_clinical = "clinical_service" in by_family
        has_workforce = "workforce" in by_family

        missing_families = []
        if not has_env:
            missing_families.append("environmental")
        if not (has_clinical or has_workforce):
            missing_families.append("clinical_or_workforce")

        # Check environmental screening
        env_exceeded = False
        env_details = []
        if has_env:
            for ev in by_family["environmental"]:
                thresh = environmental_thresholds.get(ev.metric_code)
                if thresh is not None and ev.observed >= thresh:
                    env_exceeded = True
                    env_details.append(f"{ev.metric_code} ({ev.observed}) exceeded screening threshold ({thresh})")

        # Check health/workforce anomaly
        health_anomaly = False
        health_details = []
        health_residuals = []

        for family in ["clinical_service", "workforce", "workplace_safety"]:
            for ev in by_family.get(family, []):
                if ev.is_anomaly or ev.standardised_residual > 2.0:
                    health_anomaly = True
                    health_details.append(f"{family}:{ev.metric_code} elevated (obs={ev.observed}, exp={ev.expected}, z={ev.standardised_residual})")
                    health_residuals.append(ev.standardised_residual)

        # Classification
        if env_exceeded and health_anomaly:
            evidence_class = "corroborated_health_warning"
            # Bounded score computation
            max_z = max(health_residuals) if health_residuals else 2.0
            score = min(90.0, 50.0 + max_z * 10.0)
            severity = "warning" if score < 75.0 else "critical"
            reasons.append("Environmental exceedance corroborated with elevated health/workforce contacts in the same district window.")
            reasons.extend(env_details)
            reasons.extend(health_details)
            should_alert = True

        elif env_exceeded and not health_anomaly:
            evidence_class = "environmental_watch"
            score = 45.0
            severity = "watch"
            reasons.append("Environmental hazard screening threshold exceeded; preparing preventive watch. No health anomaly observed yet.")
            reasons.extend(env_details)
            should_alert = True

        elif not env_exceeded and health_anomaly:
            evidence_class = "uncorroborated_health_anomaly"
            max_z = max(health_residuals) if health_residuals else 2.0
            score = min(70.0, 40.0 + max_z * 8.0)
            severity = "advisory" if score < 60.0 else "watch"
            reasons.append("Elevated health/workforce signal observed without concurrent environmental hazard exceedance. Requires operational review.")
            reasons.extend(health_details)
            should_alert = True

        else:
            evidence_class = "insufficient_data" if len(evidences) == 0 else "environmental_watch"
            score = 15.0
            severity = "advisory"
            reasons.append("All signals within expected statistical baselines and environmental safety thresholds.")
            should_alert = False

        return FusionDecision(
            hazard=hazard,
            evidence_class=evidence_class,
            severity=severity,
            evidence_score=round(score, 1),
            should_alert=should_alert,
            reasons=reasons,
            contributing_evidences=evidences,
            missing_families=missing_families,
            policy_version=self.policy_version,
        )

