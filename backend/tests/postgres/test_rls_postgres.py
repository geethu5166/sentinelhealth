"""PostgreSQL Row-Level Security (RLS) Integration Test Suite.

Phase 1B: PostgreSQL Security & Multi-Tenant RLS Policy Verification.

This test suite strictly connects to live PostgreSQL using the runtime role
`sentinel_app` (configured with NOBYPASSRLS) and evaluates database-level RLS
policies directly using raw SQL WITHOUT ANY application-level `WHERE tenant_id = ...`!

Mandatory Test Requirements:
1. No tenant context:
   - SELECT on protected tables & views returns 0 rows.
   - Disallowed INSERT fails RLS WITH CHECK policy (InsufficientPrivilegeError).
   - Disallowed UPDATE on hidden rows affects 0 rows (UPDATE 0).
2. Tenant A context:
   - Only Tenant A protected rows accessible across tables and views.
3. Tenant B context:
   - Only Tenant B protected rows accessible across tables and views.
4. Cross-tenant writes:
   - Inserting a Tenant B row while scoped to Tenant A raises InsufficientPrivilegeError.
   - Updating a visible Tenant A row to set tenant_id = Tenant B raises InsufficientPrivilegeError.
   - Updating Tenant B's row while scoped to Tenant A affects 0 rows (UPDATE 0).
5. Transaction isolation:
   - SET LOCAL does not leak across COMMIT or ROLLBACK.
6. Pooled connection hygiene:
   - RESET app.current_tenant_id clears tenant context so connection is unprivileged.
7. Runtime role privileges:
   - current_user is sentinel_app, rolsuper = false, rolbypassrls = false, DDL fails.
8. Authentication bootstrap flow:
   - sentinel_app can query memberships and users to resolve token-to-tenant.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from typing import Any, AsyncGenerator, Dict, Tuple
from urllib.parse import urlparse

import asyncpg
import pytest
import pytest_asyncio

logger = logging.getLogger(__name__)

# Fixed deterministic test UUIDs
TENANT_A_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
TENANT_B_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")

USER_A_ID = uuid.UUID("aaaaaaaa-1111-1111-1111-aaaaaaaaaaaa")
USER_B_ID = uuid.UUID("bbbbbbbb-2222-2222-2222-bbbbbbbbbbbb")

GEO_A_ID = uuid.UUID("a0000001-0000-0000-0000-000000000001")
GEO_B_ID = uuid.UUID("b0000001-0000-0000-0000-000000000001")

DATA_SOURCE_A_ID = uuid.UUID("a0000002-0000-0000-0000-000000000002")
DATA_SOURCE_B_ID = uuid.UUID("b0000002-0000-0000-0000-000000000002")

ALERT_A_ID = uuid.UUID("a0000003-0000-0000-0000-000000000003")
ALERT_B_ID = uuid.UUID("b0000003-0000-0000-0000-000000000003")

TASK_A_ID = uuid.UUID("a0000004-0000-0000-0000-000000000004")
TASK_B_ID = uuid.UUID("b0000004-0000-0000-0000-000000000004")

OBS_A_ID = uuid.UUID("a0000005-0000-0000-0000-000000000005")
OBS_B_ID = uuid.UUID("b0000005-0000-0000-0000-000000000005")


def parse_db_url(url: str, default_user: str, default_pass: str) -> Dict[str, Any]:
    """Parse PostgreSQL connection URL into asyncpg connect parameters."""
    clean_url = (
        url.replace("postgresql+asyncpg://", "postgres://")
        .replace("postgresql+psycopg://", "postgres://")
        .replace("postgresql://", "postgres://")
    )
    parsed = urlparse(clean_url)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "database": parsed.path.lstrip("/") if parsed.path else "sentinelhealth",
        "user": parsed.username or default_user,
        "password": parsed.password or default_pass,
    }


def get_postgres_connection_params() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Resolve connection parameters for sentinel_app and sentinel_migrator."""
    default_db = os.getenv("POSTGRES_DB", "sentinelhealth")
    default_host = os.getenv("POSTGRES_HOST", "localhost")
    default_port = int(os.getenv("POSTGRES_PORT", "5432"))

    default_app_user = os.getenv("APP_DB_USER", "sentinel_app")
    default_app_pass = os.getenv("APP_DB_PASSWORD", "sentinel_app_pass_2024")

    default_mig_user = os.getenv("MIGRATOR_DB_USER", "sentinel_migrator")
    default_mig_pass = os.getenv("MIGRATOR_DB_PASSWORD", "sentinel_migrator_pass_2024")

    app_url = (
        os.getenv("SENTINEL_TEST_POSTGRES_APP_URL")
        or os.getenv("SENTINEL_DATABASE_URL")
        or os.getenv("DATABASE_URL")
    )
    if app_url and "://" in app_url:
        app_params = parse_db_url(app_url, default_app_user, default_app_pass)
    else:
        app_params = {
            "host": default_host,
            "port": default_port,
            "database": default_db,
            "user": default_app_user,
            "password": default_app_pass,
        }

    mig_url = (
        os.getenv("SENTINEL_TEST_POSTGRES_MIGRATOR_URL")
        or os.getenv("SENTINEL_MIGRATION_DATABASE_URL")
    )
    if mig_url and "://" in mig_url:
        migrator_params = parse_db_url(mig_url, default_mig_user, default_mig_pass)
    else:
        migrator_params = {
            "host": app_params.get("host", default_host),
            "port": app_params.get("port", default_port),
            "database": app_params.get("database", default_db),
            "user": default_mig_user,
            "password": default_mig_pass,
        }

    return app_params, migrator_params


async def check_postgres_availability() -> Tuple[bool, str, Dict[str, Any], Dict[str, Any]]:
    """Probe PostgreSQL connectivity across standard ports."""
    app_params, migrator_params = get_postgres_connection_params()
    ports_to_try = [app_params["port"]]
    for fallback_port in [5433, 5432, 5434]:
        if fallback_port not in ports_to_try:
            ports_to_try.append(fallback_port)

    last_error = ""
    for test_port in ports_to_try:
        candidate_app = {**app_params, "port": test_port}
        candidate_mig = {**migrator_params, "port": test_port}
        try:
            conn = await asyncio.wait_for(
                asyncpg.connect(**candidate_app, timeout=1.5),
                timeout=2.0,
            )
            await conn.close()
            return True, "", candidate_app, candidate_mig
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {str(exc)}"

    return False, last_error, app_params, migrator_params


# Module-level availability probe
_is_available, _connect_err, _detected_app_params, _detected_migrator_params = (
    asyncio.run(check_postgres_availability())
)


@pytest.fixture(scope="session", autouse=True)
def require_live_postgres():
    """Ensure PostgreSQL is reachable; fail immediately if unavailable (no skips allowed)."""
    if not _is_available:
        pytest.fail(
            f"Mandatory PostgreSQL RLS integration tests require live PostgreSQL with roles. "
            f"Connection probe failed: {_connect_err}. Skips are prohibited for security verification."
        )


@pytest_asyncio.fixture(scope="session")
async def seed_test_database() -> AsyncGenerator[Dict[str, Any], None]:
    """Seed Tenant A and Tenant B test entities idempotently before running RLS tests."""
    conn = None
    try:
        conn = await asyncpg.connect(**_detected_migrator_params)
    except Exception:
        conn = await asyncpg.connect(**_detected_app_params)

    try:
        # 1. Ensure test tenants exist
        await conn.execute(
            """
            INSERT INTO tenants (id, name, slug, is_active)
            VALUES
                ($1, 'Sentinel Health District Alpha', 'rls_district_alpha', true),
                ($2, 'Greenfield Safety Beta', 'rls_greenfield_beta', true)
            ON CONFLICT (id) DO UPDATE SET is_active = true;
            """,
            TENANT_A_ID,
            TENANT_B_ID,
        )

        # 2. Ensure test users exist
        await conn.execute(
            """
            INSERT INTO users (id, external_id, email, display_name, is_active)
            VALUES
                ($1, 'ext-analyst-alpha', 'analyst.alpha@test.sentinelhealth', 'Analyst Alpha', true),
                ($2, 'ext-safety-beta', 'safety.beta@test.sentinelhealth', 'Safety Manager Beta', true)
            ON CONFLICT (id) DO UPDATE SET is_active = true;
            """,
            USER_A_ID,
            USER_B_ID,
        )

        # 3. Ensure memberships exist (Tenant A analyst, Tenant B safety manager)
        await conn.execute(
            """
            INSERT INTO memberships (id, user_id, tenant_id, role, is_active)
            VALUES
                (gen_random_uuid(), $1, $2, 'public_health_analyst', true),
                (gen_random_uuid(), $3, $4, 'workplace_safety_manager', true)
            ON CONFLICT (user_id, tenant_id, role) DO UPDATE SET is_active = true;
            """,
            USER_A_ID,
            TENANT_A_ID,
            USER_B_ID,
            TENANT_B_ID,
        )

        # 4. Data sources
        await conn.execute(
            """
            INSERT INTO data_sources (
                id, tenant_id, code, name, signal_family, source_type, provider,
                schema_version, expected_cadence_minutes, freshness_threshold_minutes, is_active
            )
            VALUES
                ($1, $2, 'DS-RLS-A', 'Clinic Data Source A', 'clinical_service', 'connector', 'synthetic_clinic', '1.0', 60, 180, true),
                ($3, $4, 'DS-RLS-B', 'Plant Sensor Source B', 'workforce', 'connector', 'synthetic_ehs', '1.0', 60, 180, true)
            ON CONFLICT (id) DO NOTHING;
            """,
            DATA_SOURCE_A_ID,
            TENANT_A_ID,
            DATA_SOURCE_B_ID,
            TENANT_B_ID,
        )

        # 5. Geographies (Protected table subject to RLS)
        await conn.execute("SELECT set_config('app.current_tenant_id', $1, false);", str(TENANT_A_ID))
        await conn.execute(
            """
            INSERT INTO geographies (id, tenant_id, code, name, level, is_active)
            VALUES ($1, $2, 'GEO-A-001', 'Dhanpur Surveillance Ward 1', 'ward', true)
            ON CONFLICT (id) DO NOTHING;
            """,
            GEO_A_ID,
            TENANT_A_ID,
        )

        await conn.execute("SELECT set_config('app.current_tenant_id', $1, false);", str(TENANT_B_ID))
        await conn.execute(
            """
            INSERT INTO geographies (id, tenant_id, code, name, level, is_active)
            VALUES ($1, $2, 'GEO-B-001', 'Lakshmi Foundry Complex Site', 'site', true)
            ON CONFLICT (id) DO NOTHING;
            """,
            GEO_B_ID,
            TENANT_B_ID,
        )

        # 6. Alerts (Protected table subject to RLS)
        await conn.execute("SELECT set_config('app.current_tenant_id', $1, false);", str(TENANT_A_ID))
        await conn.execute(
            """
            INSERT INTO alerts (
                id, tenant_id, hazard, evidence_class, severity, status,
                geography_id, target_period_start, target_period_end, first_detected_at, responsible_role
            )
            VALUES (
                $1, $2, 'heat_illness', 'environmental_watch', 'watch', 'new',
                $3, NOW() - INTERVAL '2 hours', NOW(), NOW() - INTERVAL '2 hours', 'public_health_analyst'
            )
            ON CONFLICT (id) DO NOTHING;
            """,
            ALERT_A_ID,
            TENANT_A_ID,
            GEO_A_ID,
        )

        await conn.execute("SELECT set_config('app.current_tenant_id', $1, false);", str(TENANT_B_ID))
        await conn.execute(
            """
            INSERT INTO alerts (
                id, tenant_id, hazard, evidence_class, severity, status,
                geography_id, target_period_start, target_period_end, first_detected_at, responsible_role
            )
            VALUES (
                $1, $2, 'workplace_safety', 'safety_escalation', 'critical', 'new',
                $3, NOW() - INTERVAL '2 hours', NOW(), NOW() - INTERVAL '2 hours', 'workplace_safety_manager'
            )
            ON CONFLICT (id) DO NOTHING;
            """,
            ALERT_B_ID,
            TENANT_B_ID,
            GEO_B_ID,
        )

        # 7. Preventive tasks (Protected table subject to RLS)
        await conn.execute("SELECT set_config('app.current_tenant_id', $1, false);", str(TENANT_A_ID))
        await conn.execute(
            """
            INSERT INTO preventive_tasks (id, tenant_id, alert_id, title, assigned_role, status)
            VALUES ($1, $2, $3, 'Issue public hydration advisory', 'public_health_analyst', 'pending')
            ON CONFLICT (id) DO NOTHING;
            """,
            TASK_A_ID,
            TENANT_A_ID,
            ALERT_A_ID,
        )

        await conn.execute("SELECT set_config('app.current_tenant_id', $1, false);", str(TENANT_B_ID))
        await conn.execute(
            """
            INSERT INTO preventive_tasks (id, tenant_id, alert_id, title, assigned_role, status)
            VALUES ($1, $2, $3, 'Urgent safety-lead review: assess on-site heat exposure and activate approved heat-response procedure', 'workplace_safety_manager', 'pending')
            ON CONFLICT (id) DO NOTHING;
            """,
            TASK_B_ID,
            TENANT_B_ID,
            ALERT_B_ID,
        )

        # 8. Signal Records / Observations (Protected table subject to RLS)
        await conn.execute("SELECT set_config('app.current_tenant_id', $1, false);", str(TENANT_A_ID))
        await conn.execute(
            """
            INSERT INTO signal_records (
                id, tenant_id, source_id, source_record_id, record_version, schema_version,
                signal_family, metric_code, value, unit, period_start, period_end, observed_at, source_available_at
            )
            VALUES (
                $1, $2, $3, 'rec-a-001', 1, '1.0',
                'clinical_service', 'heat_ed_visits', 8, 'count',
                NOW() - INTERVAL '1 hour', NOW(), NOW() - INTERVAL '1 hour', NOW()
            )
            ON CONFLICT (id) DO NOTHING;
            """,
            OBS_A_ID,
            TENANT_A_ID,
            DATA_SOURCE_A_ID,
        )

        await conn.execute("SELECT set_config('app.current_tenant_id', $1, false);", str(TENANT_B_ID))
        await conn.execute(
            """
            INSERT INTO signal_records (
                id, tenant_id, source_id, source_record_id, record_version, schema_version,
                signal_family, metric_code, value, unit, period_start, period_end, observed_at, source_available_at
            )
            VALUES (
                $1, $2, $3, 'rec-b-001', 1, '1.0',
                'workforce', 'heat_exhaustion_incidents', 4, 'count',
                NOW() - INTERVAL '1 hour', NOW(), NOW() - INTERVAL '1 hour', NOW()
            )
            ON CONFLICT (id) DO NOTHING;
            """,
            OBS_B_ID,
            TENANT_B_ID,
            DATA_SOURCE_B_ID,
        )

        # Clear session tenant variable
        await conn.execute("SELECT set_config('app.current_tenant_id', '', false);")

        yield {
            "tenant_a_id": TENANT_A_ID,
            "tenant_b_id": TENANT_B_ID,
            "alert_a_id": ALERT_A_ID,
            "alert_b_id": ALERT_B_ID,
            "task_a_id": TASK_A_ID,
            "task_b_id": TASK_B_ID,
            "obs_a_id": OBS_A_ID,
            "obs_b_id": OBS_B_ID,
            "geo_a_id": GEO_A_ID,
            "geo_b_id": GEO_B_ID,
            "user_a_id": USER_A_ID,
            "user_b_id": USER_B_ID,
        }

    finally:
        if conn:
            try:
                await conn.execute("SELECT set_config('app.current_tenant_id', '', false);")
            except Exception:
                pass
            await conn.close()


@pytest_asyncio.fixture
async def app_conn(seed_test_database) -> AsyncGenerator[asyncpg.Connection, None]:
    """Provide a dedicated asyncpg connection authenticated strictly as `sentinel_app`."""
    conn = await asyncpg.connect(**_detected_app_params)
    try:
        # Confirm user is runtime application role with NOBYPASSRLS
        current_user = await conn.fetchval("SELECT current_user;")
        assert current_user == "sentinel_app", f"Expected connection as 'sentinel_app', got '{current_user}'"
        yield conn
    finally:
        try:
            await conn.execute("SELECT set_config('app.current_tenant_id', '', false);")
        except Exception:
            pass
        await conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# Test Suite: PostgreSQL Row-Level Security (RLS) Verification
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_no_tenant_context_denied(app_conn: asyncpg.Connection, seed_test_database: Dict[str, Any]):
    """Test 1: Without SET LOCAL app.current_tenant_id, SELECT returns 0 rows.

    Protected tables and views tested: alerts, geographies, preventive_tasks, tasks view,
    signal_records, observations view.
    RAW SQL only — no application-level WHERE tenant_id = ...!
    Verifies that:
    - SELECT returns 0 rows.
    - Disallowed UPDATE on hidden rows affects 0 rows (UPDATE 0).
    - INSERT fails database RLS WITH CHECK policy (InsufficientPrivilegeError).
    """
    # 1. SELECT and UPDATE checks on unprivileged session
    async with app_conn.transaction():
        await app_conn.execute("SELECT set_config('app.current_tenant_id', '', true);")

        count_alerts = await app_conn.fetchval("SELECT COUNT(*) FROM alerts;")
        assert count_alerts == 0, f"Expected 0 alerts without tenant context, got {count_alerts}"

        count_geos = await app_conn.fetchval("SELECT COUNT(*) FROM geographies;")
        assert count_geos == 0, f"Expected 0 geographies without tenant context, got {count_geos}"

        count_tasks = await app_conn.fetchval("SELECT COUNT(*) FROM preventive_tasks;")
        assert count_tasks == 0, f"Expected 0 preventive_tasks without tenant context, got {count_tasks}"

        count_view_tasks = await app_conn.fetchval("SELECT COUNT(*) FROM tasks;")
        assert count_view_tasks == 0, f"Expected 0 tasks from view without tenant context, got {count_view_tasks}"

        count_signals = await app_conn.fetchval("SELECT COUNT(*) FROM signal_records;")
        assert count_signals == 0, f"Expected 0 signal_records without tenant context, got {count_signals}"

        count_obs = await app_conn.fetchval("SELECT COUNT(*) FROM observations;")
        assert count_obs == 0, f"Expected 0 observations from view without tenant context, got {count_obs}"

        # UPDATE without tenant context must affect 0 rows (row is invisible under USING clause)
        update_result = await app_conn.execute(
            """
            UPDATE alerts
            SET severity = 'critical'
            WHERE id = $1;
            """,
            seed_test_database["alert_a_id"],
        )
        assert update_result == "UPDATE 0", f"Expected UPDATE 0 on hidden alert, got {update_result}"

        update_task_result = await app_conn.execute(
            """
            UPDATE preventive_tasks
            SET title = 'Hijacked Task Title'
            WHERE id = $1;
            """,
            seed_test_database["task_a_id"],
        )
        assert update_task_result == "UPDATE 0", f"Expected UPDATE 0 on hidden task, got {update_task_result}"

    # 2. INSERT without tenant context must fail RLS WITH CHECK policy (in its own transaction)
    async with app_conn.transaction():
        await app_conn.execute("SELECT set_config('app.current_tenant_id', '', true);")
        unauth_alert_id = uuid.uuid4()
        with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError) as exc_info:
            await app_conn.execute(
                """
                INSERT INTO alerts (
                    id, tenant_id, hazard, evidence_class, severity, status,
                    geography_id, target_period_start, target_period_end, first_detected_at
                )
                VALUES (
                    $1, $2, 'heat_illness', 'environmental_watch', 'watch', 'new',
                    $3, NOW(), NOW(), NOW()
                );
                """,
                unauth_alert_id,
                seed_test_database["tenant_a_id"],
                seed_test_database["geo_a_id"],
            )
        assert "violates row-level security policy" in str(exc_info.value)


@pytest.mark.asyncio
async def test_tenant_a_isolation(app_conn: asyncpg.Connection, seed_test_database: Dict[str, Any]):
    """Test 2: With SET LOCAL app.current_tenant_id = '<tenant_a_uuid>', SELECT returns only Tenant A rows.

    RAW SQL only without application-level WHERE tenant_id = ...!
    """
    tenant_a_id = seed_test_database["tenant_a_id"]
    tenant_b_id = seed_test_database["tenant_b_id"]

    async with app_conn.transaction():
        await app_conn.execute("SELECT set_config('app.current_tenant_id', $1, true);", str(tenant_a_id))

        # 1. Alerts
        alerts = await app_conn.fetch("SELECT id, tenant_id, hazard, severity FROM alerts;")
        assert len(alerts) > 0, "Tenant A should see its alerts"
        for row in alerts:
            assert row["tenant_id"] == tenant_a_id, f"Leaked alert belonging to {row['tenant_id']}"
            assert row["tenant_id"] != tenant_b_id

        # 2. Geographies
        geos = await app_conn.fetch("SELECT id, tenant_id, code FROM geographies;")
        assert len(geos) > 0, "Tenant A should see its geographies"
        for row in geos:
            assert row["tenant_id"] == tenant_a_id, f"Leaked geography belonging to {row['tenant_id']}"
            assert row["tenant_id"] != tenant_b_id

        # 3. Preventive Tasks / tasks view
        tasks = await app_conn.fetch("SELECT id, tenant_id, title FROM preventive_tasks;")
        assert len(tasks) > 0, "Tenant A should see its tasks"
        for row in tasks:
            assert row["tenant_id"] == tenant_a_id, f"Leaked task belonging to {row['tenant_id']}"
            assert row["tenant_id"] != tenant_b_id

        view_tasks = await app_conn.fetch("SELECT id, tenant_id, title FROM tasks;")
        assert len(view_tasks) > 0, "Tenant A should see its tasks via view"
        for row in view_tasks:
            assert row["tenant_id"] == tenant_a_id

        # 4. Signal records / observations view
        signals = await app_conn.fetch("SELECT id, tenant_id, metric_code FROM signal_records;")
        assert len(signals) > 0, "Tenant A should see its signal records"
        for row in signals:
            assert row["tenant_id"] == tenant_a_id, f"Leaked signal record belonging to {row['tenant_id']}"
            assert row["tenant_id"] != tenant_b_id

        view_obs = await app_conn.fetch("SELECT id, tenant_id, metric_code FROM observations;")
        assert len(view_obs) > 0, "Tenant A should see its observations via view"
        for row in view_obs:
            assert row["tenant_id"] == tenant_a_id


@pytest.mark.asyncio
async def test_tenant_b_isolation(app_conn: asyncpg.Connection, seed_test_database: Dict[str, Any]):
    """Test 3: With SET LOCAL app.current_tenant_id = '<tenant_b_uuid>', SELECT returns only Tenant B rows.

    RAW SQL only without application-level WHERE tenant_id = ...!
    """
    tenant_a_id = seed_test_database["tenant_a_id"]
    tenant_b_id = seed_test_database["tenant_b_id"]

    async with app_conn.transaction():
        await app_conn.execute("SELECT set_config('app.current_tenant_id', $1, true);", str(tenant_b_id))

        # 1. Alerts
        alerts = await app_conn.fetch("SELECT id, tenant_id, hazard, severity FROM alerts;")
        assert len(alerts) > 0, "Tenant B should see its alerts"
        for row in alerts:
            assert row["tenant_id"] == tenant_b_id, f"Leaked alert belonging to {row['tenant_id']}"
            assert row["tenant_id"] != tenant_a_id

        # 2. Geographies
        geos = await app_conn.fetch("SELECT id, tenant_id, code FROM geographies;")
        assert len(geos) > 0, "Tenant B should see its geographies"
        for row in geos:
            assert row["tenant_id"] == tenant_b_id, f"Leaked geography belonging to {row['tenant_id']}"
            assert row["tenant_id"] != tenant_a_id

        # 3. Preventive Tasks / tasks view
        tasks = await app_conn.fetch("SELECT id, tenant_id, title FROM preventive_tasks;")
        assert len(tasks) > 0, "Tenant B should see its tasks"
        for row in tasks:
            assert row["tenant_id"] == tenant_b_id, f"Leaked task belonging to {row['tenant_id']}"
            assert row["tenant_id"] != tenant_a_id

        view_tasks = await app_conn.fetch("SELECT id, tenant_id, title FROM tasks;")
        assert len(view_tasks) > 0, "Tenant B should see its tasks via view"
        for row in view_tasks:
            assert row["tenant_id"] == tenant_b_id

        # 4. Signal records / observations view
        signals = await app_conn.fetch("SELECT id, tenant_id, metric_code FROM signal_records;")
        assert len(signals) > 0, "Tenant B should see its signal records"
        for row in signals:
            assert row["tenant_id"] == tenant_b_id, f"Leaked signal record belonging to {row['tenant_id']}"
            assert row["tenant_id"] != tenant_a_id

        view_obs = await app_conn.fetch("SELECT id, tenant_id, metric_code FROM observations;")
        assert len(view_obs) > 0, "Tenant B should see its observations via view"
        for row in view_obs:
            assert row["tenant_id"] == tenant_b_id


@pytest.mark.asyncio
async def test_cross_tenant_write_rejected(app_conn: asyncpg.Connection, seed_test_database: Dict[str, Any]):
    """Test 4: Cross-tenant write and update behavior under PostgreSQL RLS:

    - Inserting Tenant B record while scoped to Tenant A raises InsufficientPrivilegeError (WITH CHECK violation).
    - Updating a visible Tenant A record to set tenant_id = Tenant B raises InsufficientPrivilegeError (WITH CHECK violation).
    - Updating Tenant B's record while scoped to Tenant A modifies 0 rows (UPDATE 0, hidden under USING clause).
    """
    tenant_a_id = seed_test_database["tenant_a_id"]
    tenant_b_id = seed_test_database["tenant_b_id"]
    alert_a_id = seed_test_database["alert_a_id"]
    alert_b_id = seed_test_database["alert_b_id"]
    task_b_id = seed_test_database["task_b_id"]
    geo_b_id = seed_test_database["geo_b_id"]

    # 1. Attempt to INSERT a record carrying Tenant B's tenant_id -> Rejected by WITH CHECK
    async with app_conn.transaction():
        await app_conn.execute("SELECT set_config('app.current_tenant_id', $1, true);", str(tenant_a_id))
        forged_alert_id = uuid.uuid4()
        with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError) as exc_info:
            await app_conn.execute(
                """
                INSERT INTO alerts (
                    id, tenant_id, hazard, evidence_class, severity, status,
                    geography_id, target_period_start, target_period_end, first_detected_at
                )
                VALUES (
                    $1, $2, 'workplace_safety', 'safety_escalation', 'critical', 'new',
                    $3, NOW(), NOW(), NOW()
                );
                """,
                forged_alert_id,
                tenant_b_id,
                geo_b_id,
            )
        assert "violates row-level security policy" in str(exc_info.value)

    # 2. Attempt to UPDATE Tenant A's visible row to change its tenant_id to Tenant B -> Rejected by WITH CHECK
    async with app_conn.transaction():
        await app_conn.execute("SELECT set_config('app.current_tenant_id', $1, true);", str(tenant_a_id))
        with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError) as exc_info2:
            await app_conn.execute(
                """
                UPDATE alerts
                SET tenant_id = $1
                WHERE id = $2;
                """,
                tenant_b_id,
                alert_a_id,
            )
        assert "violates row-level security policy" in str(exc_info2.value)

    # 3. Attempt to UPDATE Tenant B's existing row while scoped to Tenant A
    # Since Tenant B's row is invisible under USING clause, exactly 0 rows are modified (UPDATE 0)
    async with app_conn.transaction():
        await app_conn.execute("SELECT set_config('app.current_tenant_id', $1, true);", str(tenant_a_id))
        update_foreign_alert = await app_conn.execute(
            """
            UPDATE alerts
            SET severity = 'emergency'
            WHERE id = $1;
            """,
            alert_b_id,
        )
        assert update_foreign_alert == "UPDATE 0", f"Cross-tenant alert update should affect 0 rows, got {update_foreign_alert}"

        update_foreign_task = await app_conn.execute(
            """
            UPDATE preventive_tasks
            SET title = 'Malicious Cross-Tenant Modification'
            WHERE id = $1;
            """,
            task_b_id,
        )
        assert update_foreign_task == "UPDATE 0", f"Cross-tenant task update should affect 0 rows, got {update_foreign_task}"


@pytest.mark.asyncio
async def test_transaction_rollback_and_commit_isolation(
    app_conn: asyncpg.Connection, seed_test_database: Dict[str, Any]
):
    """Test 5: Tenant context set via SET LOCAL does not leak into subsequent transactions on the same connection.

    Verifies across commit and rollback lifecycles.
    """
    tenant_a_id = seed_test_database["tenant_a_id"]
    tenant_b_id = seed_test_database["tenant_b_id"]

    # ── Transaction 1: SET LOCAL Tenant A -> Commit ──
    async with app_conn.transaction():
        await app_conn.execute("SELECT set_config('app.current_tenant_id', $1, true);", str(tenant_a_id))
        count_a = await app_conn.fetchval("SELECT COUNT(*) FROM alerts;")
        assert count_a > 0

    # ── Transaction 2: Same connection, subsequent transaction WITHOUT setting context ──
    async with app_conn.transaction():
        # Setting must have automatically reverted to default
        current_setting = await app_conn.fetchval("SELECT current_setting('app.current_tenant_id', true);")
        assert current_setting in ("", None), f"Expected empty setting, got '{current_setting}'"
        count_clean = await app_conn.fetchval("SELECT COUNT(*) FROM alerts;")
        assert count_clean == 0, f"Context leaked after commit! Saw {count_clean} alerts"

    # ── Transaction 3: SET LOCAL Tenant B -> Rollback ──
    try:
        async with app_conn.transaction():
            await app_conn.execute("SELECT set_config('app.current_tenant_id', $1, true);", str(tenant_b_id))
            count_b = await app_conn.fetchval("SELECT COUNT(*) FROM alerts;")
            assert count_b > 0
            # Force intentional rollback
            raise RuntimeError("Intentional test abort for rollback verification")
    except RuntimeError:
        pass

    # ── Transaction 4: Same connection after rollback ──
    async with app_conn.transaction():
        current_setting_after_rb = await app_conn.fetchval("SELECT current_setting('app.current_tenant_id', true);")
        assert current_setting_after_rb in ("", None), f"Expected empty setting, got '{current_setting_after_rb}'"
        count_after_rb = await app_conn.fetchval("SELECT COUNT(*) FROM alerts;")
        assert count_after_rb == 0, f"Context leaked after rollback! Saw {count_after_rb} alerts"


@pytest.mark.asyncio
async def test_pooled_connection_reset(app_conn: asyncpg.Connection, seed_test_database: Dict[str, Any]):
    """Test 6: RESET app.current_tenant_id clears session variable so subsequent operations are unprivileged.

    Emulates connection pool release / re-acquisition hygiene.
    """
    tenant_a_id = seed_test_database["tenant_a_id"]

    # 1. Set at session scope (as might happen if SET rather than SET LOCAL was used)
    await app_conn.execute("SELECT set_config('app.current_tenant_id', $1, false);", str(tenant_a_id))
    active_setting = await app_conn.fetchval("SELECT current_setting('app.current_tenant_id', true);")
    assert active_setting == str(tenant_a_id)

    # 2. Application connection cleanup executes RESET app.current_tenant_id
    await app_conn.execute("SELECT set_config('app.current_tenant_id', '', false);")

    # 3. Verify session variable is cleared
    cleared_setting = await app_conn.fetchval("SELECT current_setting('app.current_tenant_id', true);")
    assert cleared_setting in ("", None), f"Expected empty setting after RESET, got '{cleared_setting}'"

    # 4. Subsequent queries on the pooled connection are strictly unprivileged
    count = await app_conn.fetchval("SELECT COUNT(*) FROM alerts;")
    assert count == 0, f"Pooled connection retained privileges after RESET! Saw {count} alerts"


@pytest.mark.asyncio
async def test_runtime_role_privileges(app_conn: asyncpg.Connection):
    """Test 7: Verifies that current_user is sentinel_app, rolsuper = false, rolbypassrls = false,

    and attempts to CREATE TABLE in public schema fail with permission denied.
    """
    # 1. Check current role identity
    user = await app_conn.fetchval("SELECT current_user;")
    assert user == "sentinel_app", f"Expected current_user 'sentinel_app', got '{user}'"

    # 2. Inspect role attributes in pg_roles
    role_row = await app_conn.fetchrow(
        """
        SELECT rolname, rolsuper, rolbypassrls, rolcanlogin
        FROM pg_roles
        WHERE rolname = current_user;
        """
    )
    assert role_row is not None, "Could not fetch pg_roles for current_user"
    assert role_row["rolsuper"] is False, "CRITICAL: sentinel_app must not have superuser privileges!"
    assert role_row["rolbypassrls"] is False, "CRITICAL: sentinel_app must not have BYPASSRLS privileges!"
    assert role_row["rolcanlogin"] is True, "sentinel_app must be a login role"

    # 3. DDL attempt: CREATE TABLE in public schema must fail with permission denied
    with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError) as exc_info:
        await app_conn.execute("CREATE TABLE public.privilege_probe (id int);")
    assert "permission denied for schema public" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_membership_bootstrap_flow(app_conn: asyncpg.Connection, seed_test_database: Dict[str, Any]):
    """Test 8: Verifies that sentinel_app can query memberships for token-to-tenant resolution

    WITHOUT needing RLS bypass or prior tenant context.
    """
    # Explicitly ensure NO tenant context is configured
    await app_conn.execute("SELECT set_config('app.current_tenant_id', '', false);")

    # sentinel_app must be able to read user memberships to resolve which tenant the JWT belongs to
    rows = await app_conn.fetch(
        """
        SELECT m.id, m.user_id, m.tenant_id, m.role, u.email
        FROM memberships m
        JOIN users u ON m.user_id = u.id
        WHERE u.email = 'analyst.alpha@test.sentinelhealth';
        """
    )

    assert len(rows) > 0, "sentinel_app should be able to resolve memberships for authentication bootstrap"
    found = rows[0]
    assert found["tenant_id"] == seed_test_database["tenant_a_id"]
    assert found["role"] == "public_health_analyst"
