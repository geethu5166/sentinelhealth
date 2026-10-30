"""Authentication schemas."""

from __future__ import annotations

import uuid
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class MembershipInfo(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_name: str
    tenant_slug: str
    role: str
    scopes: Optional[dict] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class UserInfo(BaseModel):
    id: uuid.UUID
    email: str
    display_name: Optional[str] = None
    external_id: str
    is_active: bool
    current_tenant_id: Optional[uuid.UUID] = None
    current_role: Optional[str] = None
    memberships: List[MembershipInfo] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

