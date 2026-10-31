"""Alerts and evidence API endpoints."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.alerts.service import AlertService
from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.alert import Alert, AlertEvidence, AlertStateEvent, Hazard
from app.models.playbook import Recommendation
from app.privacy.suppression import default_disclosure_checker
from app.schemas.alert import (
    AlertDetail,
    AlertEvidenceRead,
    AlertStateEventRead,
    AlertSummary,
    AlertTransitionRequest,
)
from app.schemas.auth import UserInfo

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=List[AlertSummary])
async def list_alerts(
    hazard: Optional[str] = None,
    severity: Optional[str] = None,
    alert_status: Optional[str] = Query(None, alias="status"),
    geography_id: Optional[uuid.UUID] = None,
    limit: int = Query(default=50, le=100),
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists surveillance alerts with operational status and severity badges."""
    query = (
        select(Alert)
        .options(selectinload(Alert.geography), selectinload(Alert.workplace))
        .where(Alert.tenant_id == current_user.current_tenant_id)
    )
    if hazard:
        try:
            validated_hazard = Hazard(hazard)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid hazard: '{hazard}'. Allowed values: {[h.value for h in Hazard]}",
            )
        query = query.where(Alert.hazard == validated_hazard)
    if severity:
        query = query.where(Alert.severity == severity)
    if alert_status:
        query = query.where(Alert.status == alert_status)
    if geography_id:
        query = query.where(Alert.geography_id == geography_id)

    query = query.order_by(Alert.first_detected_at.desc()).limit(limit)
    result = await db.execute(query)
    alerts = result.scalars().all()

    return [
        AlertSummary(
            id=a.id,
            tenant_id=a.tenant_id,
            hazard=a.hazard.value,
            evidence_class=a.evidence_class.value,
            severity=a.severity.value,
            status=a.status.value,
            geography_id=a.geography_id,
            geography_name=a.geography.name if a.geography else "District",
            workplace_id=a.workplace_id,
            workplace_name=a.workplace.name if a.workplace else None,
            target_period_start=a.target_period_start,
            target_period_end=a.target_period_end,
            first_detected_at=a.first_detected_at,
            latest_revision_at=a.latest_revision_at,
            episode_key=a.episode_key,
            responsible_role=a.responsible_role,
            evidence_score=a.evidence_score,
            suppression_status=a.suppression_status,
            created_at=a.created_at,
        )
        for a in alerts
    ]


@router.get("/{alert_id}", response_model=AlertDetail)
async def get_alert(
    alert_id: uuid.UUID,
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves full alert package with observed/expected timeline and recommendations."""
    query = (
        select(Alert)
        .options(
            selectinload(Alert.geography),
            selectinload(Alert.workplace),
            selectinload(Alert.evidences),
            selectinload(Alert.state_events),
        )
        .where(
            Alert.id == alert_id,
            Alert.tenant_id == current_user.current_tenant_id,
        )
    )
    result = await db.execute(query)
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    # Fetch associated recommendation if available
    rec_res = await db.execute(select(Recommendation).where(Recommendation.alert_id == alert.id))
    rec = rec_res.scalars().first()

    # Privacy filter on evidences
    protected_evidences = []
    for ev in alert.evidences:
        is_sensitive = ev.signal_family in ["clinical_service", "workforce"]
        suppress, _ = default_disclosure_checker.should_suppress_cell(
            value=ev.observed_value,
            is_sensitive_health_event=is_sensitive,
        )
        protected_evidences.append(
            AlertEvidenceRead(
                id=ev.id,
                signal_family=ev.signal_family,
                source_id=ev.source_id,
                metric_code=ev.metric_code,
                observed_value=None if suppress else ev.observed_value,
                expected_value=None if suppress else ev.expected_value,
                excess=None if suppress else ev.excess,
                rate_difference=None if suppress else ev.rate_difference,
                standardised_residual=ev.standardised_residual,
                prediction_interval_lower=None if suppress else ev.prediction_interval_lower,
                prediction_interval_upper=None if suppress else ev.prediction_interval_upper,
                ewma_value=ev.ewma_value,
                ewma_threshold=ev.ewma_threshold,
                baseline_period_start=ev.baseline_period_start,
                baseline_period_end=ev.baseline_period_end,
                source_freshness_minutes=ev.source_freshness_minutes,
                data_label=ev.data_label,
                model_type=ev.model_type,
                model_version=ev.model_version,
                is_suppressed=suppress,
            )
        )

    state_events = [
        AlertStateEventRead(
            id=ev.id,
            from_status=ev.from_status,
            to_status=ev.to_status,
            actor_id=ev.actor_id,
            reason=ev.reason,
            event_metadata=getattr(ev, "metadata_", getattr(ev, "event_metadata", None)),
            created_at=ev.created_at,
        )
        for ev in alert.state_events
    ]

    return AlertDetail(
        id=alert.id,
        tenant_id=alert.tenant_id,
        hazard=alert.hazard.value,
        evidence_class=alert.evidence_class.value,
        severity=alert.severity.value,
        status=alert.status.value,
        geography_id=alert.geography_id,
        geography_name=alert.geography.name if alert.geography else "District",
        workplace_id=alert.workplace_id,
        workplace_name=alert.workplace.name if alert.workplace else None,
        target_period_start=alert.target_period_start,
        target_period_end=alert.target_period_end,
        first_detected_at=alert.first_detected_at,
        latest_revision_at=alert.latest_revision_at,
        episode_key=alert.episode_key,
        responsible_role=alert.responsible_role,
        evidence_score=alert.evidence_score,
        evidence_score_components=alert.evidence_score_components,
        suppression_status=alert.suppression_status,
        suppression_reason=alert.suppression_reason,
        playbook_id=alert.playbook_id,
        privacy_policy_version=alert.privacy_policy_version,
        evidences=protected_evidences,
        state_events=state_events,
        recommended_action=rec.recommended_action if rec else None,
        recommendation_assumptions=rec.assumptions if rec else None,
        created_at=alert.created_at,
    )


@router.get("/{alert_id}/evidence", response_model=List[AlertEvidenceRead])
async def get_alert_evidence(
    alert_id: uuid.UUID,
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns granular contributing evidence for an alert with privacy suppression."""
    query = (
        select(AlertEvidence)
        .join(Alert)
        .where(
            AlertEvidence.alert_id == alert_id,
            Alert.tenant_id == current_user.current_tenant_id,
        )
    )
    result = await db.execute(query)
    evidences = result.scalars().all()

    items = []
    for ev in evidences:
        is_sensitive = ev.signal_family in ["clinical_service", "workforce"]
        suppress, _ = default_disclosure_checker.should_suppress_cell(
            value=ev.observed_value,
            is_sensitive_health_event=is_sensitive,
        )
        items.append(
            AlertEvidenceRead(
                id=ev.id,
                signal_family=ev.signal_family,
                source_id=ev.source_id,
                metric_code=ev.metric_code,
                observed_value=None if suppress else ev.observed_value,
                expected_value=None if suppress else ev.expected_value,
                excess=None if suppress else ev.excess,
                rate_difference=None if suppress else ev.rate_difference,
                standardised_residual=ev.standardised_residual,
                prediction_interval_lower=None if suppress else ev.prediction_interval_lower,
                prediction_interval_upper=None if suppress else ev.prediction_interval_upper,
                ewma_value=ev.ewma_value,
                ewma_threshold=ev.ewma_threshold,
                source_freshness_minutes=ev.source_freshness_minutes,
                data_label=ev.data_label,
                is_suppressed=suppress,
            )
        )
    return items


@router.post("/{alert_id}/transitions", response_model=AlertSummary)
async def transition_alert_status(
    alert_id: uuid.UUID,
    payload: AlertTransitionRequest,
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Executes a validated alert status change and records an immutable audit reason."""
    service = AlertService(db)
    updated_alert = await service.transition_alert(
        alert_id=alert_id,
        tenant_id=current_user.current_tenant_id,
        to_status_str=payload.to_status,
        actor_id=current_user.id,
        reason=payload.reason,
        metadata=payload.metadata,
    )
    return AlertSummary(
        id=updated_alert.id,
        tenant_id=updated_alert.tenant_id,
        hazard=updated_alert.hazard.value,
        evidence_class=updated_alert.evidence_class.value,
        severity=updated_alert.severity.value,
        status=updated_alert.status.value,
        geography_id=updated_alert.geography_id,
        workplace_id=updated_alert.workplace_id,
        target_period_start=updated_alert.target_period_start,
        target_period_end=updated_alert.target_period_end,
        first_detected_at=updated_alert.first_detected_at,
        latest_revision_at=updated_alert.latest_revision_at,
        episode_key=updated_alert.episode_key,
        responsible_role=updated_alert.responsible_role,
        evidence_score=updated_alert.evidence_score,
        suppression_status=updated_alert.suppression_status,
        created_at=updated_alert.created_at,
    )

