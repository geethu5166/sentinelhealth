"""Playbooks API routes."""

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.playbook import Playbook
from app.schemas.auth import UserInfo

router = APIRouter(prefix="/playbooks", tags=["playbooks"])


@router.get("")
async def list_playbooks(
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists pre-approved, versioned preventive playbooks."""
    query = select(Playbook).where(
        (Playbook.tenant_id == current_user.current_tenant_id) | (Playbook.tenant_id.is_(None))
    )
    result = await db.execute(query)
    playbooks = result.scalars().all()
    return playbooks

