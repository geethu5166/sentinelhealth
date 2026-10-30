"""Preventive tasks management API routes."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.alert import Alert
from app.models.playbook import PreventiveTask, TaskEvent, TaskStatus
from app.schemas.auth import UserInfo
from app.schemas.task import TaskCreateRequest, TaskDetail, TaskSummary, TaskUpdateRequest

router = APIRouter(tags=["tasks"])


@router.get("/tasks", response_model=List[TaskSummary])
async def list_tasks(
    task_status: Optional[str] = Query(None, alias="status"),
    assigned_role: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists preventive tasks assigned to responsible roles or the current user."""
    query = select(PreventiveTask).where(PreventiveTask.tenant_id == current_user.current_tenant_id)
    if task_status:
        query = query.where(PreventiveTask.status == task_status)
    if assigned_role:
        query = query.where(PreventiveTask.assigned_role == assigned_role)

    query = query.order_by(PreventiveTask.priority.desc(), PreventiveTask.due_at.asc()).limit(limit)
    result = await db.execute(query)
    tasks = result.scalars().all()

    return [
        TaskSummary(
            id=t.id,
            tenant_id=t.tenant_id,
            alert_id=t.alert_id,
            title=t.title,
            assigned_role=t.assigned_role,
            assigned_to_user_id=t.assigned_to_user_id,
            status=t.status.value,
            priority=t.priority,
            due_at=t.due_at,
            completed_at=t.completed_at,
            approval_required=t.approval_required,
            created_at=t.created_at,
        )
        for t in tasks
    ]


@router.post("/alerts/{alert_id}/tasks", response_model=TaskSummary)
async def create_alert_task(
    alert_id: uuid.UUID,
    payload: TaskCreateRequest,
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Creates a new accountable preventive action task linked to an alert."""
    # Verify alert exists and belongs to current tenant
    alert_res = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.tenant_id == current_user.current_tenant_id)
    )
    alert = alert_res.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    task = PreventiveTask(
        tenant_id=current_user.current_tenant_id,
        alert_id=alert.id,
        recommendation_id=payload.recommendation_id,
        title=payload.title,
        description=payload.description,
        assigned_role=payload.assigned_role,
        assigned_to_user_id=payload.assigned_to_user_id,
        status=TaskStatus.PENDING,
        priority=payload.priority,
        due_at=payload.due_at,
        approval_required=payload.approval_required,
    )
    db.add(task)
    await db.flush()

    event = TaskEvent(
        task_id=task.id,
        from_status=None,
        to_status=TaskStatus.PENDING.value,
        actor_id=current_user.id,
        reason="Manual task creation by operator",
    )
    db.add(event)
    await db.commit()
    await db.refresh(task)

    return TaskSummary(
        id=task.id,
        tenant_id=task.tenant_id,
        alert_id=task.alert_id,
        title=task.title,
        assigned_role=task.assigned_role,
        assigned_to_user_id=task.assigned_to_user_id,
        status=task.status.value,
        priority=task.priority,
        due_at=task.due_at,
        completed_at=task.completed_at,
        approval_required=task.approval_required,
        created_at=task.created_at,
    )


@router.get("/tasks/{task_id}", response_model=TaskDetail)
async def get_task_by_id(
    task_id: uuid.UUID,
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves a single task by ID with alert details, strictly scoped by tenant."""
    query = (
        select(PreventiveTask)
        .options(selectinload(PreventiveTask.alert))
        .where(
            PreventiveTask.id == task_id,
            PreventiveTask.tenant_id == current_user.current_tenant_id,
        )
    )
    res = await db.execute(query)
    task = res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    return TaskDetail(
        id=task.id,
        tenant_id=task.tenant_id,
        alert_id=task.alert_id,
        title=task.title,
        description=task.description,
        recommendation_id=task.recommendation_id,
        assigned_role=task.assigned_role,
        assigned_to_user_id=task.assigned_to_user_id,
        status=task.status.value,
        priority=task.priority,
        due_at=task.due_at,
        completed_at=task.completed_at,
        completion_evidence=task.completion_evidence,
        completion_notes=task.completion_notes,
        approval_required=task.approval_required,
        approved_by=task.approved_by,
        approved_at=task.approved_at,
        alert_hazard=task.alert.hazard.value if task.alert else None,
        alert_severity=task.alert.severity.value if task.alert else None,
        created_at=task.created_at,
    )


@router.patch("/tasks/{task_id}", response_model=TaskDetail)
async def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdateRequest,
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Updates task status, completion evidence, or approval determination."""
    query = (
        select(PreventiveTask)
        .options(selectinload(PreventiveTask.alert))
        .where(
            PreventiveTask.id == task_id,
            PreventiveTask.tenant_id == current_user.current_tenant_id,
        )
    )
    res = await db.execute(query)
    task = res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    from_status_val = task.status.value

    if payload.status:
        try:
            task.status = TaskStatus(payload.status)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task status")

        if task.status == TaskStatus.COMPLETED:
            task.completed_at = datetime.now(timezone.utc)

    if payload.assigned_to_user_id is not None:
        task.assigned_to_user_id = payload.assigned_to_user_id

    if payload.completion_evidence is not None:
        task.completion_evidence = payload.completion_evidence

    if payload.completion_notes is not None:
        task.completion_notes = payload.completion_notes

    if payload.approval_decision:
        if payload.approval_decision == "approved":
            task.approved_by = current_user.id
            task.approved_at = datetime.now(timezone.utc)
            task.status = TaskStatus.COMPLETED

    event = TaskEvent(
        task_id=task.id,
        from_status=from_status_val,
        to_status=task.status.value,
        actor_id=current_user.id,
        reason="Task status update",
        evidence=payload.completion_evidence,
    )
    db.add(event)
    await db.commit()
    await db.refresh(task)

    return TaskDetail(
        id=task.id,
        tenant_id=task.tenant_id,
        alert_id=task.alert_id,
        title=task.title,
        description=task.description,
        recommendation_id=task.recommendation_id,
        assigned_role=task.assigned_role,
        assigned_to_user_id=task.assigned_to_user_id,
        status=task.status.value,
        priority=task.priority,
        due_at=task.due_at,
        completed_at=task.completed_at,
        completion_evidence=task.completion_evidence,
        completion_notes=task.completion_notes,
        approval_required=task.approval_required,
        approved_by=task.approved_by,
        approved_at=task.approved_at,
        alert_hazard=task.alert.hazard.value if task.alert else None,
        alert_severity=task.alert.severity.value if task.alert else None,
        created_at=task.created_at,
    )

