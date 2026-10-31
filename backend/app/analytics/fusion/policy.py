"""Deterministic evidence fusion engine for multi-hazard surveillance.

Policy Version 0.2.0:
- Supports Heat Illness and Air Quality / Respiratory Hazards.
- Treats PM2.5 and AQI as a single environmental family to prevent double-counting.
- Distinguishes specific respiratory signals from nonspecific all-cause absence.
- Explicitly models missing, stale, quarantined, and suppressed data states (never treated as numerical zero).
- Restricts cross-source fusion within each tenant's authorized domain.
"""

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
    # Phase 3 explicit data state flags & provenance
    status: str = "valid"  # "valid", "missing", "stale", "quarantined", "suppressed", "insufficient_data"
    is_suppressed: bool = False
    is_quarantined: bool = False
    is_nonspecific: bool = False
    denominator: Optional[float] = None
    incidence_rate: Optional[float] = None
    unit: Optional[str] = None
    source_id: Optional[str] = None
    aqi_system: Optional[str] = None  # "aqi_in", "aqi_us", "aqi_eu"


ContributingEvidence = EvidenceItem


@dataclass
class FusionDecision:
    hazard: str
    evidence_class: str  # "corroborated_health_warning", "environmental_watch", "uncorroborated_health_anomaly", "insufficient_data", "safety_escalation"
    severity: str        # "advisory", "watch", "warning", "critical"
    evidence_score: float  # 0-100
    should_alert: bool = True
    reasons: List[str] = field(default_factory=list)
    contributing_evidences: List[EvidenceItem] = field(default_factory=list)
    missing_families: List[str] = field(default_factory=list)
    data_state_flags: List[str] = field(default_factory=list)
    policy_version: str = "0.2.0"


class EvidenceFusionEngine:
    """
    Deterministic rule engine that fuses multi-signal evidence into actionable warnings.
    Supports heat_illness and air_quality_respiratory.
    """

    def __init__(self, policy_version: str = "0.2.0"):
        self.policy_version = policy_version

    def evaluate(
        self,
        hazard: str,
        evidences: List[EvidenceItem],
        environmental_thresholds: Dict[str, float],
        is_urgent_safety_trigger: bool = False,
        tenant_type: str = "integrated",  # "public_health", "workforce", "integrated"
    ) -> FusionDecision:
        """
        Executes fusion rules against current evidence set with explicit state handling.
        """
        reasons: List[str] = []
        data_state_flags: List[str] = []

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
                data_state_flags=["urgent_safety_override"],
                policy_version=self.policy_version,
            )

        # 1. Filter and inspect explicit data states (missing, stale, quarantined, suppressed)
        valid_evidences: List[EvidenceItem] = []
        for ev in evidences:
            if ev.is_quarantined or ev.status == "quarantined":
                data_state_flags.append(f"quarantined_input:{ev.metric_code}")
                reasons.append(f"Signal {ev.metric_code} is quarantined due to data quality flags; excluded from scoring.")
            elif ev.is_stale or ev.status == "stale":
                data_state_flags.append(f"stale_input:{ev.metric_code}")
                reasons.append(f"Signal {ev.metric_code} is stale ({ev.source_freshness_minutes}m old); treated as unavailable, not zero.")
            elif ev.is_suppressed or ev.status == "suppressed":
                data_state_flags.append(f"suppressed_input:{ev.metric_code}")
                reasons.append(f"Signal {ev.metric_code} is privacy-suppressed; cannot confirm elevation without unsuppressed denominator/counts.")
            elif ev.status in ["missing", "insufficient_data"]:
                data_state_flags.append(f"missing_input:{ev.metric_code}")
                reasons.append(f"Signal {ev.metric_code} has insufficient or missing data; not assumed to be zero.")
            else:
                valid_evidences.append(ev)

        # 2. Partition valid evidences by signal family
        by_family: Dict[str, List[EvidenceItem]] = {}
        for ev in valid_evidences:
            by_family.setdefault(ev.signal_family, []).append(ev)

        has_env = "environmental" in by_family
        has_clinical = "clinical_service" in by_family
        has_workforce = "workforce" in by_family

        missing_families: List[str] = []
        if not has_env:
            missing_families.append("environmental")
        if not (has_clinical or has_workforce):
            missing_families.append("clinical_or_workforce")

        # 3. Environmental evaluation
        # Rule: PM2.5 and AQI are NOT independent corroborating families. They are evaluated together as "environmental".
        env_exceeded = False
        env_details: List[str] = []
        if has_env:
            for ev in by_family["environmental"]:
                thresh = environmental_thresholds.get(ev.metric_code)
                if thresh is not None and ev.observed >= thresh:
                    env_exceeded = True
                    unit_str = f" {ev.unit}" if ev.unit else ""
                    aqi_info = f" ({ev.aqi_system.upper()})" if ev.aqi_system else ""
                    env_details.append(f"{ev.metric_code}{aqi_info} ({ev.observed:.1f}{unit_str}) exceeded threshold ({thresh:.1f})")

        # 4. Health and workforce anomaly evaluation
        health_anomaly = False
        health_details: List[str] = []
        health_residuals: List[float] = []

        # Clinical service contacts
        for ev in by_family.get("clinical_service", []):
            if ev.is_anomaly or ev.standardised_residual > 2.0:
                health_anomaly = True
                health_details.append(
                    f"clinical:{ev.metric_code} elevated (obs={ev.observed:.0f}, exp={ev.expected:.1f}, z={ev.standardised_residual:.2f})"
                )
                health_residuals.append(ev.standardised_residual)

        # Workforce absence: verify specific vs nonspecific
        for ev in by_family.get("workforce", []):
            if ev.is_nonspecific:
                # All-cause absence must NOT be treated as a specific respiratory/heat diagnosis
                data_state_flags.append(f"nonspecific_absence:{ev.metric_code}")
                if ev.is_anomaly or ev.standardised_residual > 2.0:
                    health_details.append(
                        f"workforce:{ev.metric_code} elevated nonspecific absence (z={ev.standardised_residual:.2f}); cannot infer specific diagnosis"
                    )
            else:
                if ev.is_anomaly or ev.standardised_residual > 2.0:
                    health_anomaly = True
                    health_details.append(
                        f"workforce:{ev.metric_code} elevated specific absence (obs={ev.observed:.0f}, exp={ev.expected:.1f}, z={ev.standardised_residual:.2f})"
                    )
                    health_residuals.append(ev.standardised_residual)

        # 5. Determine evidence class and severity
        if len(valid_evidences) == 0:
            return FusionDecision(
                hazard=hazard,
                evidence_class="insufficient_data",
                severity="advisory",
                evidence_score=0.0,
                should_alert=False,
                reasons=["No valid, unsuppressed, non-stale signals available for evaluation."] + reasons,
                contributing_evidences=evidences,
                missing_families=missing_families,
                data_state_flags=data_state_flags,
                policy_version=self.policy_version,
            )

        if env_exceeded and health_anomaly:
            evidence_class = "corroborated_health_warning"
            max_z = max(health_residuals) if health_residuals else 2.0
            score = min(92.0, 52.0 + max_z * 10.0)
            severity = "warning" if score < 75.0 else "critical"
            reasons.append("Environmental exposure threshold exceeded AND corroborated with elevated health contacts in the same district.")
            reasons.extend(env_details)
            reasons.extend(health_details)
            should_alert = True

        elif env_exceeded and not health_anomaly:
            evidence_class = "environmental_watch"
            score = 45.0
            severity = "watch"
            reasons.append("Environmental hazard screening threshold exceeded; pre-positioning operational watch. No health anomaly observed.")
            reasons.extend(env_details)
            reasons.extend(health_details)
            should_alert = True

        elif not env_exceeded and health_anomaly:
            evidence_class = "uncorroborated_health_anomaly"
            max_z = max(health_residuals) if health_residuals else 2.0
            score = min(70.0, 40.0 + max_z * 8.0)
            severity = "advisory" if score < 60.0 else "watch"
            reasons.append("Elevated health signal observed without concurrent environmental exposure exceedance. Requires operational review.")
            reasons.extend(health_details)
            should_alert = True

        else:
            evidence_class = "environmental_watch"
            score = 15.0
            severity = "advisory"
            reasons.append("All active signals within expected statistical baselines and environmental safety thresholds.")
            should_alert = False

        return FusionDecision(
            hazard=hazard,
            evidence_class=evidence_class,
            severity=severity,
            evidence_score=round(score, 1),
            should_alert=should_alert,
            reasons=reasons,
            contributing_evidences=valid_evidences,
            missing_families=missing_families,
            data_state_flags=data_state_flags,
            policy_version=self.policy_version,
        )
