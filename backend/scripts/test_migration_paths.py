"""Test migration execution across both empty database and upgrade path."""

import asyncio
import subprocess
import asyncpg


async def test_migration_paths():
    print("[*] Testing migration path 1: Empty database -> all migrations (001 -> 002)...")
    # Use postgres superuser on unix socket to manage test databases
    subprocess.run("sudo -u postgres psql -p 5433 -c 'DROP DATABASE IF EXISTS sentinelhealth_test_fresh;'", shell=True, check=True)
    subprocess.run("sudo -u postgres psql -p 5433 -c 'CREATE DATABASE sentinelhealth_test_fresh;'", shell=True, check=True)

    # Create extensions in new db
    subprocess.run("sudo -u postgres psql -p 5433 -d sentinelhealth_test_fresh -c 'CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"; CREATE EXTENSION IF NOT EXISTS \"postgis\";'", shell=True, check=True)
    subprocess.run("sudo -u postgres psql -p 5433 -d sentinelhealth_test_fresh -c 'GRANT ALL PRIVILEGES ON DATABASE sentinelhealth_test_fresh TO sentinel_migrator;'", shell=True, check=True)
    subprocess.run("sudo -u postgres psql -p 5433 -d sentinelhealth_test_fresh -c 'GRANT CONNECT ON DATABASE sentinelhealth_test_fresh TO sentinel_app;'", shell=True, check=True)
    subprocess.run("sudo -u postgres psql -p 5433 -d sentinelhealth_test_fresh -c 'GRANT USAGE, CREATE ON SCHEMA public TO sentinel_migrator;'", shell=True, check=True)
    subprocess.run("sudo -u postgres psql -p 5433 -d sentinelhealth_test_fresh -c 'GRANT USAGE ON SCHEMA public TO sentinel_app;'", shell=True, check=True)
    subprocess.run("sudo -u postgres psql -p 5433 -d sentinelhealth_test_fresh -c 'ALTER DEFAULT PRIVILEGES FOR ROLE sentinel_migrator IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO sentinel_app;'", shell=True, check=True)
    subprocess.run("sudo -u postgres psql -p 5433 -d sentinelhealth_test_fresh -c 'ALTER DEFAULT PRIVILEGES FOR ROLE sentinel_migrator IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO sentinel_app;'", shell=True, check=True)

    # Step A: Upgrade to head from empty
    cmd = (
        "cd /mnt/c/Users/geete/Hack2skills/sentinelhealth/backend && "
        "SENTINEL_MIGRATION_DATABASE_URL=postgresql+asyncpg://sentinel_migrator:sentinel_migrator_pass_2024@localhost:5433/sentinelhealth_test_fresh "
        "python3 -m alembic upgrade head"
    )
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print("[!] Upgrade failed:\n", res.stderr)
        raise RuntimeError("Empty DB migration failed!")
    print("[+] All migrations applied successfully on fresh database.")

    # Verify version and constraint
    check_conn = await asyncpg.connect("postgresql://sentinel_migrator:sentinel_migrator_pass_2024@localhost:5433/sentinelhealth_test_fresh")
    v = await check_conn.fetchval("SELECT version_num FROM alembic_version")
    c = await check_conn.fetchval("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'uq_signal_records_idempotency'")
    print(f"[+] Fresh DB Final Alembic Version: {v}")
    print(f"[+] Fresh DB Constraint Definition: {c}")
    assert v == "002_signal_record_idempotency"
    assert "geography_id" in c and "workplace_id" in c

    # Step B: Downgrade to 001_initial_schema
    print("\n[*] Testing downgrade path: 002 -> 001_initial_schema...")
    cmd_down = (
        "cd /mnt/c/Users/geete/Hack2skills/sentinelhealth/backend && "
        "SENTINEL_MIGRATION_DATABASE_URL=postgresql+asyncpg://sentinel_migrator:sentinel_migrator_pass_2024@localhost:5433/sentinelhealth_test_fresh "
        "python3 -m alembic downgrade 001_initial_schema"
    )
    res_down = subprocess.run(cmd_down, shell=True, capture_output=True, text=True)
    assert res_down.returncode == 0, f"Downgrade failed: {res_down.stderr}"
    v_down = await check_conn.fetchval("SELECT version_num FROM alembic_version")
    c_down = await check_conn.fetchval("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'uq_signal_records_idempotency'")
    print(f"[+] Downgraded Alembic Version: {v_down}")
    print(f"[+] Constraint after downgrade: {c_down}")
    assert v_down == "001_initial_schema"
    assert c_down is None

    # Step C: Upgrade from previous schema (001 -> 002)
    print("\n[*] Testing upgrade path: Database at previous schema (001) -> new migration (002)...")
    res_up = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    assert res_up.returncode == 0, f"Re-upgrade failed: {res_up.stderr}"
    v_up = await check_conn.fetchval("SELECT version_num FROM alembic_version")
    c_up = await check_conn.fetchval("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'uq_signal_records_idempotency'")
    print(f"[+] Re-upgraded Alembic Version: {v_up}")
    print(f"[+] Constraint after re-upgrade: {c_up}")
    assert v_up == "002_signal_record_idempotency"
    assert "geography_id" in c_up and "workplace_id" in c_up

    await check_conn.close()

    # Clean up test database
    subprocess.run("sudo -u postgres psql -p 5433 -c 'DROP DATABASE sentinelhealth_test_fresh;'", shell=True, check=True)
    print("\n[+] SUCCESS: Both empty database installation and previous-schema upgrade paths verified perfectly!")


if __name__ == "__main__":
    asyncio.run(test_migration_paths())
