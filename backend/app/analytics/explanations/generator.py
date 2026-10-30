"""Deterministic explanation generator for health surveillance alerts."""

from __future__ import annotations

from typing import Any, Dict, List
from app.analytics.fusion.policy import FusionDecision


class AlertExplanationGenerator:
    """
    Generates structured, privacy-safe, non-causal explanations for surveillance warnings.
    Ref: Spec requirement on explainable analytics with deterministic templates.
    """

    @staticmethod
    def generate_explanation(decision: FusionDecision, geography_name: str) -> Dict[str, Any]:
        """
        Builds a comprehensive explanation package without causal assertions or privacy leakage.
        """
        conditions_met = []
        conditions_not_met = []
        alternate_explanations = [
            "Local reporting artifacts, batch transmission, or catch-up submissions from clinical centers.",
            "Independent non-occupational community gatherings or seasonal social events.",
            "Shift rescheduling or temporary workforce redeployment across production lines.",
        ]

        if decision.evidence_class == "corroborated_health_warning":
            headline = f"Potential elevated health risk warning in {geography_name}"
            summary = (
                f"Statistical surveillance identified an unusual increase in reported health/workforce signals in {geography_name} "
                f"that coincided in time and geography with elevated environmental hazard readings. "
                f"Surveillance signals indicate statistical co-occurrence, which requires operational investigation but does not prove causation."
            )
            conditions_met.extend([
                "Environmental screening threshold exceeded for the target period.",
                "Health/workforce count exceeded upper prediction boundary of the baseline model.",
                "Multiple signal families satisfied temporal and geographical alignment criteria.",
            ])
        elif decision.evidence_class == "environmental_watch":
            headline = f"Environmental preventive watch active in {geography_name}"
            summary = (
                f"Environmental screening thresholds were reached in {geography_name}. "
                f"No unusual increase in health service contacts or sickness absence has been detected in current reports. "
                f"Pre-emptive preventative readiness is recommended under the approved site safety plan."
            )
            conditions_met.append("Environmental screening threshold exceeded.")
            conditions_not_met.append("No abnormal health or sickness absence signal detected (rates within normal baseline).")
        elif decision.evidence_class == "uncorroborated_health_anomaly":
            headline = f"Uncorroborated health signal increase under review in {geography_name}"
            summary = (
                f"Anomalous increases were detected in health or workforce reports in {geography_name}, "
                f"without concurrent environmental screening exceedance. "
                f"This may reflect indoor environmental factors, process changes, or reporting variations."
            )
            conditions_met.append("Health or workforce signal exceeded expected statistical baseline.")
            conditions_not_met.append("Environmental indicators remained within normal baseline limits.")
        else:
            headline = f"Surveillance assessment notice for {geography_name}"
            summary = "Routine monitoring active. No alert conditions met."

        return {
            "headline": headline,
            "summary": summary,
            "evidence_class": decision.evidence_class,
            "severity": decision.severity,
            "evidence_score": decision.evidence_score,
            "conditions_met": conditions_met,
            "conditions_not_met": conditions_not_met,
            "alternate_explanations": alternate_explanations,
            "disclaimer": (
                "SentinelHealth decision support provides statistical early warnings for workforce and public health leads. "
                "It does not diagnose individuals, determine clinical fitness, or replace established safety procedures."
            ),
        }

