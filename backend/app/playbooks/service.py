"""Playbook and preventive decision support service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.playbook import (
    Playbook,
    PlaybookApprovalStatus,
    PreventiveTask,
    Recommendation,
    TaskEvent,
    TaskStatus,
)


class PlaybookService:
    """
    Matches alerts against pre-approved, versioned preventive playbooks
    and creates actionable, accountable preventive tasks.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_playbook_from_yaml(self, yaml_content: str) -> Playbook:
        data = yaml.safe_load(yaml_content)
        version = data.get("version", "1.0.0")
        hazard = data.get("hazard")

        res = await self.session.execute(
            select(Playbook).where(Playbook.hazard == hazard, Playbook.version == version)
        )
        existing = res.scalar_one_or_none()
        if existing:
            return existing

        playbook = Playbook(
            hazard=hazard,
            jurisdiction=data.get("jurisdiction", "demo_fictional"),
            sector=data.get("sector", "general_workforce"),
            evidence_requirements=data.get("evidence_requirements", {}),
            contraindications=data.get("contraindications", {}),
            action_tiers=data.get("action_tiers", {}),
            version=version,
            approval_status=PlaybookApprovalStatus.APPROVED,
            source_link=data.get("source_link"),
            source_review_date=datetime.now(timezone.utc),
        )
        self.session.add(playbook)
        await self.session.flush()
        return playbook

    async def generate_recommendation_and_task(
        self,
        alert: Alert,
        playbook: Playbook,
    ) -> Tuple[Recommendation, PreventiveTask]:
        """
        Derives proportionate action tier from alert severity and creates a preventive task.
        """
        now = datetime.now(timezone.utc)
        action_tiers = playbook.action_tiers or {}

        # Map alert severity to action tier
        tier_key = "tier_1_preparation"
        if alert.severity.value in ["warning", "critical"]:
            tier_key = "tier_2_adjusted_operations"
        elif alert.severity.value == "emergency":
            tier_key = "tier_3_restricted_activity"

        tier_config = action_tiers.get(tier_key, {
            "title": f"Review {alert.hazard.value} preventive measures",
            "action": f"Verify on-site protective controls and hydration/cooling availability under {alert.hazard.value} plan.",
            "accountable_role": "workplace_safety_manager",
            "approval_role": "occupational_health_analyst",
            "review_window_hours": 24,
            "completion_evidence_required": "Site inspection checklist confirmation",
        })

        # Check if an active task already exists for this alert episode (idempotency guard)
        existing_task_res = await self.session.execute(
            select(PreventiveTask).where(
                PreventiveTask.alert_id == alert.id,
                PreventiveTask.status.in_([TaskStatus.PENDING, TaskStatus.ACCEPTED, TaskStatus.IN_PROGRESS]),
            )
        )
        existing_task = existing_task_res.scalar_one_or_none()
        if existing_task:
            existing_rec_res = await self.session.execute(
                select(Recommendation).where(Recommendation.id == existing_task.recommendation_id)
            )
            existing_rec = existing_rec_res.scalar_one_or_none()
            if existing_rec:
                return existing_rec, existing_task

        # Create Recommendation
        rec = Recommendation(
            alert_id=alert.id,
            playbook_id=playbook.id,
            playbook_version=playbook.version,
            action_tier=tier_key,
            recommended_action=tier_config.get("action", "Initiate standard workplace mitigation."),
            accountable_role=tier_config.get("accountable_role", alert.responsible_role or "workplace_safety_manager"),
            approval_role=tier_config.get("approval_role"),
            completion_evidence_required=tier_config.get("completion_evidence_required"),
            review_window_hours=tier_config.get("review_window_hours", 24),
            assumptions={
                "environmental_measurements_representative": True,
                "workforce_capacity_normal": True,
                "water_and_rest_facilities_accessible": True,
            },
        )
        self.session.add(rec)
        await self.session.flush()

        # Create Preventive Task
        due_at = now + timedelta(hours=tier_config.get("review_window_hours", 24))
        task = PreventiveTask(
            tenant_id=alert.tenant_id,
            alert_id=alert.id,
            recommendation_id=rec.id,
            title=tier_config.get("title", f"Action: {alert.hazard.value} mitigation"),
            description=rec.recommended_action,
            assigned_role=rec.accountable_role,
            status=TaskStatus.PENDING,
            priority=2 if alert.severity.value in ["warning", "critical"] else 1,
            due_at=due_at,
            approval_required=bool(rec.approval_role),
        )
        self.session.add(task)
        await self.session.flush()

        task_event = TaskEvent(
            task_id=task.id,
            from_status=None,
            to_status=TaskStatus.PENDING.value,
            reason="Automated task generation from approved playbook",
        )
        self.session.add(task_event)
        await self.session.commit()

        return rec, task

