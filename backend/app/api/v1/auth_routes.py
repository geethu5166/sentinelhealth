"""User identity and authorization routes."""

from fastapi import APIRouter, Depends
from app.auth.dependencies import get_current_user
from app.schemas.auth import UserInfo

router = APIRouter(prefix="/me", tags=["auth"])


@router.get("", response_model=UserInfo)
async def get_my_profile(current_user: UserInfo = Depends(get_current_user)):
    """Returns authenticated user information, active tenant, and verified memberships."""
    return current_user

