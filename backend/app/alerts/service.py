"""Alert lifecycle management, deduplication, and episode tracking service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.analytics.fusion.policy import FusionDecision
from app.models.alert import (
    Alert,
    AlertEvidence,
    AlertSeverity,
    AlertStateEvent,
    AlertStatus,
    EvidenceClass,
    Hazard,
)


class AlertService:
    """
    Manages the lifecycle of surveillance warnings, deduplicating alerts into episodes
    and enforcing state machine transition rules.
    """

    ALLOWED_TRANSITIONS = {
        AlertStatus.NEW: [AlertStatus.ACKNOWLEDGED, AlertStatus.DISMISSED_DATA_ISSUE, AlertStatus.DISMISSED_NOT_ACTIONABLE],
        AlertStatus.ACKNOWLEDGED: [AlertStatus.INVESTIGATING, AlertStatus.DISMISSED_DATA_ISSUE, AlertStatus.DISMISSED_NOT_ACTIONABLE],
        AlertStatus.INVESTIGATING: [AlertStatus.ACTION_PLANNED, AlertStatus.DISMISSED_DATA_ISSUE, AlertStatus.DISMISSED_NOT_ACTIONABLE, AlertStatus.RESOLVED],
        AlertStatus.ACTION_PLANNED: [AlertStatus.MONITORING, AlertStatus.RESOLVED],
        AlertStatus.MONITORING: [AlertStatus.RESOLVED, AlertStatus.REOPENED],
        AlertStatus.RESOLVED: [AlertStatus.REOPENED],
        AlertStatus.DISMISSED_DATA_ISSUE: [AlertStatus.REOPENED],
        AlertStatus.DISMISSED_NOT_ACTIONABLE: [AlertStatus.REOPENED],
        AlertStatus.REOPENED: [AlertStatus.INVESTIGATING, AlertStatus.ACKNOWLEDGED],
    }

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_or_update_alert(
        self,
        tenant_id: uuid.UUID,
        decision: FusionDecision,
        geography_id: uuid.UUID,
        target_period_start: datetime,
        target_period_end: datetime,
        responsible_role: str,
        workplace_id: Optional[uuid.UUID] = None,
        episode_window_hours: int = 72,
    ) -> Alert:
        """
        Creates a new alert or updates an existing open episode to avoid notification flapping.
        """
        episode_key = f"{tenant_id}:{decision.hazard}:{geography_id}"
        now = datetime.now(timezone.utc)
        window_cutoff = now - timedelta(hours=episode_window_hours)

        # Look for existing active alert for this episode
        query = (
            select(Alert)
            .where(
                Alert.tenant_id == tenant_id,
                Alert.episode_key == episode_key,
                Alert.status.in_([
                    AlertStatus.NEW,
                    AlertStatus.ACKNOWLEDGED,
                    AlertStatus.INVESTIGATING,
                    AlertStatus.ACTION_PLANNED,
                    AlertStatus.MONITORING,
                ]),
                Alert.created_at >= window_cutoff,
            )
            .order_by(Alert.created_at.desc())
        )
        result = await self.session.execute(query)
        existing_alert = result.scalar_one_or_none()

        if existing_alert:
            # Update existing episode
            existing_alert.evidence_score = Decimal(str(decision.evidence_score))
            existing_alert.latest_revision_at = now
            existing_alert.target_period_end = target_period_end
            existing_alert.evidence_class = EvidenceClass(decision.evidence_class)
            existing_alert.severity = AlertSeverity(decision.severity)
            await self.session.flush()
            return existing_alert

        # Create new Alert episode
        alert = Alert(
            tenant_id=tenant_id,
            hazard=Hazard(decision.hazard),
            evidence_class=EvidenceClass(decision.evidence_class),
            severity=AlertSeverity(decision.severity),
            status=AlertStatus.NEW,
            geography_id=geography_id,
            workplace_id=workplace_id,
            target_period_start=target_period_start,
            target_period_end=target_period_end,
            first_detected_at=now,
            latest_revision_at=now,
            episode_key=episode_key,
            episode_window_start=target_period_start,
            episode_window_end=target_period_start + timedelta(hours=episode_window_hours),
            responsible_role=responsible_role,
            evidence_score=Decimal(str(decision.evidence_score)),
            evidence_score_components={"reasons": decision.reasons, "missing": decision.missing_families},
            privacy_policy_version="0.1.0",
        )
        self.session.add(alert)
        await self.session.flush()

        # Add evidence entries
        for ev in decision.contributing_evidences:
            alert_ev = AlertEvidence(
                alert_id=alert.id,
                signal_family=ev.signal_family,
                metric_code=ev.metric_code,
                observed_value=Decimal(str(ev.observed)),
                expected_value=Decimal(str(ev.expected)),
                excess=Decimal(str(ev.excess)),
                standardised_residual=Decimal(str(ev.standardised_residual)),
                ewma_value=Decimal(str(ev.ewma_value)),
                source_freshness_minutes=ev.source_freshness_minutes,
                data_label=ev.data_label,
            )
            self.session.add(alert_ev)

        # Initial state event
        event = AlertStateEvent(
            alert_id=alert.id,
            from_status=None,
            to_status=AlertStatus.NEW.value,
            actor_id=None,
            reason="Initial automated surveillance detection",
        )
        self.session.add(event)
        await self.session.flush()

        return alert

    async def transition_alert(
        self,
        alert_id: uuid.UUID,
        tenant_id: uuid.UUID,
        to_status_str: str,
        actor_id: Optional[uuid.UUID],
        reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Alert:
        """Enforces state transition rules and records an audit state event."""
        query = select(Alert).options(selectinload(Alert.state_events)).where(
            Alert.id == alert_id,
            Alert.tenant_id == tenant_id,
        )
        res = await self.session.execute(query)
        alert = res.scalar_one_or_none()
        if not alert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

        try:
            target_status = AlertStatus(to_status_str)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid target status: {to_status_str}")

        allowed = self.ALLOWED_TRANSITIONS.get(alert.status, [])
        if target_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Illegal state transition from {alert.status.value} to {target_status.value}. Allowed: {[s.value for s in allowed]}",
            )

        from_status_val = alert.status.value
        alert.status = target_status
        alert.updated_at = datetime.now(timezone.utc)

        state_event = AlertStateEvent(
            alert_id=alert.id,
            from_status=from_status_val,
            to_status=target_status.value,
            actor_id=actor_id,
            reason=reason,
            event_metadata=metadata or {},
        )
        self.session.add(state_event)

        # Append-only governance audit trail (in addition to alert state_events)
        from app.audit.service import log_audit_event

        await log_audit_event(
            self.session,
            action="alert.transition",
            resource_type="alert",
            resource_id=str(alert.id),
            tenant_id=tenant_id,
            actor_id=actor_id,
            details={
                "from_status": from_status_val,
                "to_status": target_status.value,
                "reason": reason,
                "hazard": alert.hazard.value if hasattr(alert.hazard, "value") else str(alert.hazard),
            },
        )

        await self.session.commit()
        return alert

