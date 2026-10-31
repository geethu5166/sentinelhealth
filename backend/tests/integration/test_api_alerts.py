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


@pytest.mark.asyncio
async def test_get_privacy_safe_map_layer_authenticated(client: AsyncClient, auth_headers: dict):
    """API returns privacy-safe GeoJSON FeatureCollection; never leaks exact counts or rates for suppressed cells."""
    response = await client.get("/api/v1/map-layer?metric_code=pm25_concentration", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert "features" in data

    for feat in data["features"]:
        props = feat["properties"]
        assert "geography_code" in props
        assert "status" in props
        assert props["status"] in ["elevated", "valid_non_elevated", "suppressed", "insufficient_data", "unavailable"]

        # Critical disclosure checks
        assert "contributor_count" not in props, "Exact contributor count must not be exposed in map properties"
        if props.get("is_suppressed"):
            assert props["value"] is None, "Raw metric value must be None when cell is suppressed"
            assert props["encounter_rate_per_100k"] is None, "Rate must not be calculated on suppressed numerator"
            assert "Suppressed: this group does not meet the minimum reporting threshold" in props["suppression_reason"]


@pytest.mark.asyncio
async def test_map_layer_missing_metric_produces_unavailable(client: AsyncClient, auth_headers: dict):
    """Missing or failed signals must produce 'unavailable', never a fabricated health value or suppressed result."""
    response = await client.get("/api/v1/map-layer?metric_code=non_existent_metric_999", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    for feat in data["features"]:
        props = feat["properties"]
        assert props["status"] == "unavailable"
        assert props["value"] is None
        assert props["is_suppressed"] is False


@pytest.mark.asyncio
async def test_get_replay_summary_stored_benchmark_metadata(client: AsyncClient, auth_headers: dict):
    """Replay summary endpoint returns stored synthetic benchmark results separate from tenant operational records."""
    response = await client.get("/api/v1/validation/summary", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["provenance"] == "stored_synthetic_benchmark_evaluation"
    assert data["is_live_surveillance"] is False
    assert data["is_tenant_operational_record"] is False
    assert "policy_comparisons" in data



