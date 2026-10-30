"""Integration tests for multi-tenant isolation, RLS scoping, and token validation."""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import set_tenant_context, reset_tenant_context
from app.models.tenant import Tenant, User


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(client: AsyncClient):
    """Unauthenticated access to protected endpoints must return HTTP 401."""
    response = await client.get("/api/v1/overview")
    assert response.status_code == 401
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_invalid_token_rejected(client: AsyncClient):
    """Malformed or invalid JWTs must be strictly rejected with HTTP 401."""
    invalid_headers = {"Authorization": "Bearer malformed.jwt.token.here"}
    response = await client.get("/api/v1/me", headers=invalid_headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_health_endpoints_accessible_without_auth(client: AsyncClient):
    """Liveness and readiness probes must remain accessible without authentication."""
    live_resp = await client.get("/health/live")
    assert live_resp.status_code == 200
    assert live_resp.json()["status"] == "ok"

    ready_resp = await client.get("/health/ready")
    # Must not be rejected with 401 Unauthorized
    assert ready_resp.status_code in [200, 503]
    assert ready_resp.status_code != 401
    assert "status" in ready_resp.json()


@pytest.mark.asyncio
async def test_authenticated_user_profile(client: AsyncClient, auth_headers_tenant_a: dict):
    """Authenticated request returns user profile with verified database memberships."""
    response = await client.get("/api/v1/me", headers=auth_headers_tenant_a)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "analyst@demo.local"
    assert len(data["memberships"]) > 0
    assert data["memberships"][0]["role"] == "public_health_analyst"


@pytest.mark.asyncio
async def test_cross_tenant_header_forgery_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_tenant_a: dict,
):
    """
    An authenticated user cannot access another tenant simply by passing an unassigned X-Tenant-ID.
    The server derives tenant context solely from verified DB memberships.
    """
    # Fetch Tenant B's ID
    res = await db_session.execute(select(Tenant).where(Tenant.slug == "greenfield_industries"))
    tenant_b = res.scalar_one()

    # User A (public health analyst) tries to access Tenant B (greenfield)
    forged_headers = {
        **auth_headers_tenant_a,
        "X-Tenant-ID": str(tenant_b.id),
    }
    response = await client.get("/api/v1/me", headers=forged_headers)
    assert response.status_code == 403
    assert "User does not have access to the requested tenant" in response.json()["detail"]


@pytest.mark.asyncio
async def test_pooled_connection_context_isolation(db_session: AsyncSession):
    """
    Verifies that set_tenant_context and reset_tenant_context properly clean
    the session context and prevent pooled connection context leakage.
    """
    tenant_id = uuid.uuid4()
    
    # 1. Set context
    await set_tenant_context(db_session, tenant_id)
    
    # 2. Reset context
    await reset_tenant_context(db_session)
    
    # 3. Session remains valid and clean
    res = await db_session.execute(select(Tenant))
    tenants = res.scalars().all()
    assert len(tenants) >= 2
