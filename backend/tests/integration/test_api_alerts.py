"""Integration tests for alert retrieval and state transitions."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_alerts_authenticated(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/alerts", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_illegal_state_transition_rejected(client: AsyncClient, auth_headers: dict):
    # Transitioning a non-existent alert or invalid status
    fake_id = "00000000-0000-0000-0000-000000000000"
    payload = {"to_status": "resolved", "reason": "Testing illegal transition"}
    response = await client.post(f"/api/v1/alerts/{fake_id}/transitions", json=payload, headers=auth_headers)
    assert response.status_code in [404, 400]


@pytest.mark.asyncio
async def test_cross_tenant_alert_isolation(
    client: AsyncClient,
    auth_headers_tenant_a: dict,
    auth_headers_tenant_b: dict,
):
    """Verifies that alerts retrieved by Tenant A are scoped to Tenant A and Tenant B to Tenant B."""
    resp_a = await client.get("/api/v1/alerts", headers=auth_headers_tenant_a)
    assert resp_a.status_code == 200

    resp_b = await client.get("/api/v1/alerts", headers=auth_headers_tenant_b)
    assert resp_b.status_code == 200

    alerts_a = resp_a.json()
    alerts_b = resp_b.json()

    # Alerts returned to Tenant A must not appear in Tenant B's list
    ids_a = {a["id"] for a in alerts_a}
    ids_b = {b["id"] for b in alerts_b}
    assert ids_a.isdisjoint(ids_b)


@pytest.mark.asyncio
async def test_invalid_hazard_query_parameter_rejected_422(client: AsyncClient, auth_headers: dict):
    """API must strictly reject unknown or misspelled hazard enum parameters with HTTP 422."""
    response = await client.get("/api/v1/alerts?hazard=misspelled_hazard_xyz", headers=auth_headers)
    assert response.status_code == 422
    data = response.json()
    assert "Invalid hazard" in data["detail"]


