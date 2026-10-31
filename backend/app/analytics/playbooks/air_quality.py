"""Air-Quality & Respiratory Surveillance Playbook.

Defines proportionate operational action tiers and automated recommendation generators.

Ethical & Clinical Boundaries:
- Recommends responsible-role review, verification of local exposure, and activation of approved air-quality responses.
- Explicitly DOES NOT automatically prescribe medical treatment.
- Explicitly DOES NOT impose mandatory employee restrictions without clinician review.
- Explicitly DOES NOT mandate respirator selection without fit-testing.
- Explicitly DOES NOT prescribe disciplinary measures.
"""

from __future__ import annotations

from typing import Any, Dict, List


class AirQualityPlaybook:
    """Standard operating procedures for particulate matter (PM2.5) and respiratory early warnings."""

    HAZARD = "air_quality_respiratory"
    VERSION = 1

    TIERS = {
        "tier_1_preparation": {
            "name": "Environmental Air Quality Watch",
            "trigger_condition": "PM2.5 >= 60 ug/m3 or AQI >= 150 without clinical surge",
            "recommended_actions": [
                "Verify local ambient air monitoring station readings and inspect HVAC particulate filters.",
                "Issue precautionary air-quality guidance to facilities and pre-notify vulnerable individuals (asthma, COPD).",
                "Ensure inventory of particulate protective masks (N95/FFP2) is inspected and available upon request.",
            ],
            "accountable_roles": ["workplace_safety_manager", "public_health_analyst"],
            "review_window_hours": 12,
        },
        "tier_2_adjusted_operations": {
            "name": "Corroborated Air Quality Warning",
            "trigger_condition": "PM2.5 >= 60 ug/m3 AND elevated acute respiratory encounters in district",
            "recommended_actions": [
                "Activate facility clean-air shelters and verify continuous high-efficiency air filtration.",
                "Reschedule heavy outdoor physical activities away from morning/evening stagnation inversion hours.",
                "Provide voluntary particulate protective equipment (N95/FFP2) with manufacturer usage guidance.",
                "Conduct operational review of district clinical service capacity for acute respiratory cases.",
            ],
            "accountable_roles": ["workplace_safety_manager", "occupational_health_analyst"],
            "review_window_hours": 4,
        },
        "tier_3_restricted_activity": {
            "name": "Severe Particulate Emergency",
            "trigger_condition": "PM2.5 >= 150 ug/m3 OR severe clinical surge with persistent air stagnation",
            "recommended_actions": [
                "Convene emergency management committee to review non-essential outdoor work suspension.",
                "Issue public health advisory advising sensitive groups to stay indoors.",
                "Inspect facility indoor air airlocks and exhaust dampers.",
            ],
            "accountable_roles": ["platform_admin", "workplace_safety_manager"],
            "review_window_hours": 2,
        },
    }

    BOUNDARIES = {
        "prohibit_automatic_medical_treatment": True,
        "prohibit_mandatory_individual_restrictions_without_clinician": True,
        "prohibit_respirator_mandate_without_fit_test": True,
        "prohibit_disciplinary_actions": True,
        "statutory_authority_note": (
            "SentinelHealth is a decision-support early warning system. All mitigation actions must be approved "
            "and executed by authorized operational roles in compliance with applicable occupational safety and health regulations."
        ),
    }

    @classmethod
    def generate_recommendation(
        cls,
        evidence_class: str,
        severity: str,
        evidence_summary: str,
        district_id: str = "DIST-DHANPUR",
    ) -> Dict[str, Any]:
        """Generates a structured recommendation payload for an alert."""
        if evidence_class == "corroborated_health_warning":
            tier_key = "tier_2_adjusted_operations"
        elif severity == "critical":
            tier_key = "tier_3_restricted_activity"
        else:
            tier_key = "tier_1_preparation"

        tier = cls.TIERS[tier_key]

        return {
            "hazard": cls.HAZARD,
            "playbook_version": cls.VERSION,
            "action_tier": tier_key,
            "action_tier_name": tier["name"],
            "recommended_actions": tier["recommended_actions"],
            "accountable_roles": tier["accountable_roles"],
            "review_window_hours": tier["review_window_hours"],
            "evidence_basis": evidence_summary,
            "assumptions": {
                "district": district_id,
                "exposure_threshold_ug_m3": 60.0,
                "ethical_constraints": cls.BOUNDARIES,
            },
            "completion_evidence_required": (
                "Written record of local air monitoring verification, HVAC filter check, "
                "and logged operational adjustments."
            ),
        }
