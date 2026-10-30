"""FastAPI authentication and authorization dependencies."""

from __future__ import annotations

import uuid
from typing import Annotated, Callable, List, Optional
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.oidc import TokenPayload, get_jwks, validate_token
from app.db.session import get_db, set_tenant_context
from app.models.tenant import Membership, Tenant, User, MembershipRole
from app.schemas.auth import MembershipInfo, UserInfo

security = HTTPBearer(auto_error=False)


async def get_token_payload(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> TokenPayload:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        jwks = await get_jwks()
        payload = validate_token(credentials.credentials, jwks)
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    token: Annotated[TokenPayload, Depends(get_token_payload)],
    db: Annotated[AsyncSession, Depends(get_db)],
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> UserInfo:
    """
    Resolves the authenticated user from the database.
    If the user does not exist yet (e.g. first login via Keycloak), auto-provisions them.
    Checks DB memberships to confirm authorized tenant access.
    """
    # Find user by external_id
    query = (
        select(User)
        .options(selectinload(User.memberships).selectinload(Membership.tenant))
        .where(User.external_id == token.sub)
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        # Check by email
        if token.email:
            query = (
                select(User)
                .options(selectinload(User.memberships).selectinload(Membership.tenant))
                .where(User.email == token.email)
            )
            result = await db.execute(query)
            user = result.scalar_one_or_none()

    if not user:
        # Auto-provision user in demo mode
        user = User(
            external_id=token.sub,
            email=token.email or f"{token.sub}@demo.local",
            display_name=token.preferred_username or token.email or "Demo User",
            is_active=True,
        )
        db.add(user)
        await db.flush()

        # Add default membership to primary demo tenant
        tenant_res = await db.execute(select(Tenant).where(Tenant.slug == "district_health_authority"))
        tenant = tenant_res.scalar_one_or_none()
        if tenant:
            role_to_assign = MembershipRole.PUBLIC_HEALTH_ANALYST
            if token.roles:
                for r in token.roles:
                    try:
                        role_to_assign = MembershipRole(r)
                        break
                    except ValueError:
                        pass
            membership = Membership(
                user_id=user.id,
                tenant_id=tenant.id,
                role=role_to_assign,
                is_active=True,
            )
            db.add(membership)
            await db.flush()

        # Re-fetch user with relations
        query = (
            select(User)
            .options(selectinload(User.memberships).selectinload(Membership.tenant))
            .where(User.id == user.id)
        )
        result = await db.execute(query)
        user = result.scalar_one()

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    # Determine current tenant and active membership
    active_memberships = [m for m in user.memberships if m.is_active]
    if not active_memberships:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no active organization memberships",
        )

    current_membership = active_memberships[0]
    if x_tenant_id:
        try:
            req_tenant_uuid = uuid.UUID(x_tenant_id)
            matched = [m for m in active_memberships if m.tenant_id == req_tenant_uuid]
            if matched:
                current_membership = matched[0]
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User does not have access to the requested tenant",
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid X-Tenant-ID header format",
            )

    # Set PostgreSQL RLS context
    await set_tenant_context(db, current_membership.tenant_id)

    memberships_info = [
        MembershipInfo(
            id=m.id,
            tenant_id=m.tenant_id,
            tenant_name=m.tenant.name if m.tenant else "Unknown",
            tenant_slug=m.tenant.slug if m.tenant else "unknown",
            role=m.role.value if hasattr(m.role, "value") else str(m.role),
            scopes=m.scopes,
            is_active=m.is_active,
        )
        for m in active_memberships
    ]

    return UserInfo(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        external_id=user.external_id,
        is_active=user.is_active,
        current_tenant_id=current_membership.tenant_id,
        current_role=current_membership.role.value if hasattr(current_membership.role, "value") else str(current_membership.role),
        memberships=memberships_info,
    )


def require_role(allowed_roles: List[str]) -> Callable:
    """Dependency factory checking that current user possesses one of the allowed roles."""
    async def role_checker(
        current_user: Annotated[UserInfo, Depends(get_current_user)],
    ) -> UserInfo:
        if current_user.current_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.current_role}' is not authorized for this resource. Required: {allowed_roles}",
            )
        return current_user

    return role_checker


async def require_tenant_access(
    tenant_id: uuid.UUID,
    current_user: Annotated[UserInfo, Depends(get_current_user)],
) -> UserInfo:
    """Verifies that the authenticated user has explicit membership in the requested tenant."""
    allowed_tenant_ids = [m.tenant_id for m in current_user.memberships]
    if tenant_id not in allowed_tenant_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to tenant data outside user membership",
        )
    return current_user

