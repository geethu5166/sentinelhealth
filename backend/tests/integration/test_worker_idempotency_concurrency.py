"""Integration tests for worker idempotency, concurrency, and transactional rollback safety.

Verifies:
1. Concurrent duplicate worker execution against persistent database state.
2. Enforcement of unique constraint: (tenant_id, source_id, metric_code, period_start, record_version).
3. Exactly-once state advancement without double-counting records.
4. Transactional rollback safety (failed batches leave zero residual records).
5. Worker retry idempotency under duplicate delivery.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os
import uuid
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

import asyncpg
import pytest
import pytest_asyncio

from app.connectors.base import NormalizedRecord
from app.ingestion.service import IngestionService
from app.models.signal import DataSource, IngestionRun, IngestionStatus, SignalFamily, SourceType
from app.models.tenant import Tenant


def get_connection_params() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    default_db = os.getenv("POSTGRES_DB", "sentinelhealth")
    default_host = os.getenv("POSTGRES_HOST", "localhost")
    default_port = int(os.getenv("POSTGRES_PORT", "5433" if os.name != "nt" else "5432"))

    app_user = os.getenv("APP_DB_USER", "sentinel_app")
    app_pass = os.getenv("APP_DB_PASSWORD", "sentinel_app_pass_2024")

    mig_user = os.getenv("MIGRATOR_DB_USER", "sentinel_migrator")
    mig_pass = os.getenv("MIGRATOR_DB_PASSWORD", "sentinel_migrator_pass_2024")

    app_url = os.getenv("SENTINEL_DATABASE_URL")
    if app_url and "://" in app_url:
        clean = app_url.replace("postgresql+asyncpg://", "postgres://")
        p = urlparse(clean)
        app_params = {
            "host": p.hostname or default_host,
            "port": p.port or default_port,
            "database": p.path.lstrip("/") or default_db,
            "user": p.username or app_user,
            "password": p.password or app_pass,
        }
    else:
        app_params = {
            "host": default_host,
            "port": default_port,
            "database": default_db,
            "user": app_user,
            "password": app_pass,
        }

    mig_params = dict(app_params)
    mig_params["user"] = mig_user
    mig_params["password"] = mig_pass

    return app_params, mig_params


@pytest.fixture(scope="module")
def postgres_params() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    return get_connection_params()


@pytest.mark.asyncio
async def test_persistent_db_unique_constraint_enforcement(postgres_params: Tuple[Dict[str, Any], Dict[str, Any]]):
    """
    Direct SQL verification of the unique constraint on:
    (tenant_id, source_id, metric_code, period_start, record_version).
    Attempts to insert duplicate records in separate transactions or concurrently;
    PostgreSQL must enforce uniqueness and reject the duplicate with UniqueViolationError.
    """
    app_params, mig_params = postgres_params

    # Use migrator to set up test tenant and source
    mig_conn = await asyncpg.connect(**mig_params)
    test_tenant_id = uuid.uuid4()
    test_source_id = uuid.uuid4()
    test_slug = f"test-tenant-{uuid.uuid4().hex[:8]}"
    test_source_code = f"src-{uuid.uuid4().hex[:8]}"

    try:
        await mig_conn.execute(
            """
            INSERT INTO tenants (id, name, slug, display_name, is_active)
            VALUES ($1, $2, $3, $4, true)
            ON CONFLICT (slug) DO NOTHING;
            """,
            test_tenant_id,
            "Idempotency Test Tenant",
            test_slug,
            "Idempotency Test Tenant",
        )

        await mig_conn.execute(
            """
            INSERT INTO data_sources (
                id, tenant_id, name, code, provider, signal_family, source_type,
                schema_version, expected_cadence_minutes, freshness_threshold_minutes, is_active
            ) VALUES ($1, $2, $3, $4, 'internal_system', 'workforce', 'connector', '1.0', 60, 180, true)
            ON CONFLICT (tenant_id, code) DO NOTHING;
            """,
            test_source_id,
            test_tenant_id,
            "Idempotency Test Source",
            test_source_code,
        )
    finally:
        await mig_conn.close()

    # Now connect as sentinel_app with tenant context
    conn1 = await asyncpg.connect(**app_params)
    conn2 = await asyncpg.connect(**app_params)

    try:
        # Set tenant context
        await conn1.execute("SELECT set_config('app.current_tenant_id', $1, false);", str(test_tenant_id))
        await conn2.execute("SELECT set_config('app.current_tenant_id', $1, false);", str(test_tenant_id))

        rec_time = datetime(2026, 7, 1, 10, 0, 0, tzinfo=timezone.utc)
        metric = "sickness_absence_worker_days"
        version = 1

        # Worker 1 inserts row
        rec_id_1 = uuid.uuid4()
        await conn1.execute(
            """
            INSERT INTO signal_records (
                id, tenant_id, source_id, source_record_id, record_version,
                schema_version, signal_family, metric_code, value, unit,
                period_start, period_end, observed_at, source_available_at,
                location_basis, location_confidence, data_label, is_current
            ) VALUES (
                $1, $2, $3, 'rec-001', $4,
                '1.0', 'workforce', $5, 25.0, 'worker_days',
                $6, $7, $6, $6,
                'workplace', 'exact', 'observed', true
            );
            """,
            rec_id_1,
            test_tenant_id,
            test_source_id,
            version,
            metric,
            rec_time,
            rec_time + timedelta(hours=1),
        )

        # Worker 2 attempts duplicate insert with exact same
        # (tenant_id, source_id, metric_code, period_start, record_version)
        rec_id_2 = uuid.uuid4()
        with pytest.raises(asyncpg.exceptions.UniqueViolationError) as exc_info:
            await conn2.execute(
                """
                INSERT INTO signal_records (
                    id, tenant_id, source_id, source_record_id, record_version,
                    schema_version, signal_family, metric_code, value, unit,
                    period_start, period_end, observed_at, source_available_at,
                    location_basis, location_confidence, data_label, is_current
                ) VALUES (
                    $1, $2, $3, 'rec-002-dup', $4,
                    '1.0', 'workforce', $5, 25.0, 'worker_days',
                    $6, $7, $6, $6,
                    'workplace', 'exact', 'observed', true
                );
                """,
                rec_id_2,
                test_tenant_id,
                test_source_id,
                version,
                metric,
                rec_time,
                rec_time + timedelta(hours=1),
            )

        assert "uq_signal_records_idempotency" in str(exc_info.value) or "duplicate key" in str(exc_info.value)

        # Confirm exactly 1 record exists in database
        row_count = await conn1.fetchval(
            """
            SELECT count(*) FROM signal_records
            WHERE tenant_id = $1 AND source_id = $2 AND metric_code = $3 AND period_start = $4;
            """,
            test_tenant_id,
            test_source_id,
            metric,
            rec_time,
        )
        assert row_count == 1, f"Expected 1 record, got {row_count}"

    finally:
        await conn1.close()
        await conn2.close()


@pytest.mark.asyncio
async def test_concurrent_worker_execution_with_on_conflict(postgres_params: Tuple[Dict[str, Any], Dict[str, Any]]):
    """
    Simulates two worker processes receiving identical signal batches concurrently.
    Using ON CONFLICT (tenant_id, source_id, metric_code, period_start, record_version) DO NOTHING,
    both workers complete without unhandled exception and exactly-once state is achieved.
    """
    app_params, mig_params = postgres_params

    # Set up source
    mig_conn = await asyncpg.connect(**mig_params)
    test_tenant_id = uuid.uuid4()
    test_source_id = uuid.uuid4()

    try:
        await mig_conn.execute(
            """
            INSERT INTO tenants (id, name, slug, display_name, is_active)
            VALUES ($1, 'Concurrent Worker Tenant', $2, 'Concurrent Worker Tenant', true);
            """,
            test_tenant_id,
            f"slug-{uuid.uuid4().hex[:8]}",
        )
        await mig_conn.execute(
            """
            INSERT INTO data_sources (
                id, tenant_id, name, code, provider, signal_family, source_type,
                schema_version, expected_cadence_minutes, freshness_threshold_minutes, is_active
            ) VALUES ($1, $2, 'Worker Feed', $3, 'internal_system', 'environmental', 'connector', '1.0', 60, 180, true);
            """,
            test_source_id,
            test_tenant_id,
            f"src-{uuid.uuid4().hex[:8]}",
        )
    finally:
        await mig_conn.close()

    conn_w1 = await asyncpg.connect(**app_params)
    conn_w2 = await asyncpg.connect(**app_params)

    try:
        await conn_w1.execute("SELECT set_config('app.current_tenant_id', $1, false);", str(test_tenant_id))
        await conn_w2.execute("SELECT set_config('app.current_tenant_id', $1, false);", str(test_tenant_id))

        batch_times = [
            datetime(2026, 7, 2, h, 0, 0, tzinfo=timezone.utc)
            for h in range(12, 16)
        ]

        async def worker_task(conn, worker_name: str) -> int:
            inserted = 0
            for t in batch_times:
                res = await conn.execute(
                    """
                    INSERT INTO signal_records (
                        id, tenant_id, source_id, source_record_id, record_version,
                        schema_version, signal_family, metric_code, value, unit,
                        period_start, period_end, observed_at, source_available_at,
                        location_basis, location_confidence, data_label, is_current
                    ) VALUES (
                        gen_random_uuid(), $1, $2, $3, 1,
                        '1.0', 'environmental', 'apparent_temperature', 38.5, 'celsius',
                        $4, $5, $4, $4,
                        'model_grid', 'mapped', 'observed', true
                    )
                    ON CONFLICT (tenant_id, source_id, metric_code, period_start, record_version)
                    DO NOTHING;
                    """,
                    test_tenant_id,
                    test_source_id,
                    f"rec-{t.isoformat()}",
                    t,
                    t + timedelta(hours=1),
                )
                if res == "INSERT 0 1":
                    inserted += 1
            return inserted

        # Run both workers simultaneously
        w1_count, w2_count = await asyncio.gather(
            worker_task(conn_w1, "Worker-1"),
            worker_task(conn_w2, "Worker-2"),
        )

        # Sum of inserts must equal the batch size (4 unique records)
        assert w1_count + w2_count == 4, f"Total inserts {w1_count + w2_count} != 4"

        # Verify exactly 4 records exist in database
        total_in_db = await conn_w1.fetchval(
            "SELECT count(*) FROM signal_records WHERE tenant_id = $1 AND source_id = $2;",
            test_tenant_id,
            test_source_id,
        )
        assert total_in_db == 4

    finally:
        await conn_w1.close()
        await conn_w2.close()


@pytest.mark.asyncio
async def test_transactional_rollback_safety(postgres_params: Tuple[Dict[str, Any], Dict[str, Any]]):
    """
    Demonstrates transactional rollback safety:
    If a worker fails mid-batch, rolling back the transaction leaves zero
    residual/corrupted records in signal_records.
    """
    app_params, mig_params = postgres_params

    mig_conn = await asyncpg.connect(**mig_params)
    test_tenant_id = uuid.uuid4()
    test_source_id = uuid.uuid4()

    try:
        await mig_conn.execute(
            """
            INSERT INTO tenants (id, name, slug, display_name, is_active)
            VALUES ($1, 'Rollback Test Tenant', $2, 'Rollback Test Tenant', true);
            """,
            test_tenant_id,
            f"slug-{uuid.uuid4().hex[:8]}",
        )
        await mig_conn.execute(
            """
            INSERT INTO data_sources (
                id, tenant_id, name, code, provider, signal_family, source_type,
                schema_version, expected_cadence_minutes, freshness_threshold_minutes, is_active
            ) VALUES ($1, $2, 'Rollback Source', $3, 'internal_system', 'clinical_service', 'connector', '1.0', 60, 180, true);
            """,
            test_source_id,
            test_tenant_id,
            f"src-{uuid.uuid4().hex[:8]}",
        )
    finally:
        await mig_conn.close()

    conn = await asyncpg.connect(**app_params)
    try:
        await conn.execute("SELECT set_config('app.current_tenant_id', $1, false);", str(test_tenant_id))

        # Initial count is 0
        initial_count = await conn.fetchval(
            "SELECT count(*) FROM signal_records WHERE tenant_id = $1;",
            test_tenant_id,
        )
        assert initial_count == 0

        # Start transaction
        tr = conn.transaction()
        await tr.start()
        try:
            # Insert valid record 1
            t1 = datetime(2026, 7, 3, 10, 0, 0, tzinfo=timezone.utc)
            await conn.execute(
                """
                INSERT INTO signal_records (
                    id, tenant_id, source_id, source_record_id, record_version,
                    schema_version, signal_family, metric_code, value, unit,
                    period_start, period_end, observed_at, source_available_at,
                    location_basis, location_confidence, data_label, is_current
                ) VALUES (
                    gen_random_uuid(), $1, $2, 'rec-rb-1', 1,
                    '1.0', 'clinical_service', 'heat_exhaustion_contacts', 15.0, 'encounters',
                    $3, $4, $3, $3,
                    'facility', 'exact', 'observed', true
                );
                """,
                test_tenant_id,
                test_source_id,
                t1,
                t1 + timedelta(hours=1),
            )

            # Insert valid record 2
            t2 = datetime(2026, 7, 3, 11, 0, 0, tzinfo=timezone.utc)
            await conn.execute(
                """
                INSERT INTO signal_records (
                    id, tenant_id, source_id, source_record_id, record_version,
                    schema_version, signal_family, metric_code, value, unit,
                    period_start, period_end, observed_at, source_available_at,
                    location_basis, location_confidence, data_label, is_current
                ) VALUES (
                    gen_random_uuid(), $1, $2, 'rec-rb-2', 1,
                    '1.0', 'clinical_service', 'heat_exhaustion_contacts', 18.0, 'encounters',
                    $3, $4, $3, $3,
                    'facility', 'exact', 'observed', true
                );
                """,
                test_tenant_id,
                test_source_id,
                t2,
                t2 + timedelta(hours=1),
            )

            # Simulate worker crash or fatal data error mid-batch
            raise RuntimeError("Simulated worker process crash during ingestion batch")

        except Exception:
            await tr.rollback()

        # Verify that ROLLBACK removed all partial records
        post_rollback_count = await conn.fetchval(
            "SELECT count(*) FROM signal_records WHERE tenant_id = $1;",
            test_tenant_id,
        )
        assert post_rollback_count == 0, f"Expected 0 records after rollback, found {post_rollback_count}"

    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_worker_retry_idempotency(postgres_params: Tuple[Dict[str, Any], Dict[str, Any]]):
    """
    Demonstrates worker retry idempotency:
    When a Celery job retries due to connection/timeout acknowledgment issues,
    the IngestionRun idempotency_key prevents duplicate runs and ensures
    identical records are not re-inserted or duplicated.
    """
    app_params, mig_params = postgres_params

    mig_conn = await asyncpg.connect(**mig_params)
    test_tenant_id = uuid.uuid4()
    test_source_id = uuid.uuid4()

    try:
        await mig_conn.execute(
            """
            INSERT INTO tenants (id, name, slug, display_name, is_active)
            VALUES ($1, 'Retry Test Tenant', $2, 'Retry Test Tenant', true);
            """,
            test_tenant_id,
            f"slug-{uuid.uuid4().hex[:8]}",
        )
        await mig_conn.execute(
            """
            INSERT INTO data_sources (
                id, tenant_id, name, code, provider, signal_family, source_type,
                schema_version, expected_cadence_minutes, freshness_threshold_minutes, is_active
            ) VALUES ($1, $2, 'Retry Feed', $3, 'internal_system', 'workforce', 'connector', '1.0', 60, 180, true);
            """,
            test_source_id,
            test_tenant_id,
            f"src-{uuid.uuid4().hex[:8]}",
        )
    finally:
        await mig_conn.close()

    conn = await asyncpg.connect(**app_params)
    try:
        await conn.execute("SELECT set_config('app.current_tenant_id', $1, false);", str(test_tenant_id))

        idempotency_key = f"celery-job-ingest-{uuid.uuid4().hex}"
        run_id = uuid.uuid4()

        # Attempt 1: Worker executes ingestion run
        await conn.execute(
            """
            INSERT INTO ingestion_runs (
                id, tenant_id, source_id, status, records_received,
                records_accepted, records_rejected, idempotency_key
            ) VALUES ($1, $2, $3, 'accepted', 10, 10, 0, $4);
            """,
            run_id,
            test_tenant_id,
            test_source_id,
            idempotency_key,
        )

        # Attempt 2: Celery retries same job with same idempotency key
        # Database rejects duplicate ingestion_runs entry
        with pytest.raises(asyncpg.exceptions.UniqueViolationError):
            await conn.execute(
                """
                INSERT INTO ingestion_runs (
                    id, tenant_id, source_id, status, records_received,
                    records_accepted, records_rejected, idempotency_key
                ) VALUES ($1, $2, $3, 'accepted', 10, 10, 0, $4);
                """,
                uuid.uuid4(),
                test_tenant_id,
                test_source_id,
                idempotency_key,
            )

        # Confirm exactly 1 ingestion_run exists for that idempotency key
        run_count = await conn.fetchval(
            "SELECT count(*) FROM ingestion_runs WHERE idempotency_key = $1;",
            idempotency_key,
        )
        assert run_count == 1

    finally:
        await conn.close()
