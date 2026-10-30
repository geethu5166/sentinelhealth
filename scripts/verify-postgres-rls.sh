#!/usr/bin/env bash
# verify-postgres-rls.sh — Standalone automated runner for PostgreSQL RLS integration tests
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "================================================================="
echo " SentinelHealth: PostgreSQL Row-Level Security Verification "
echo "================================================================="
echo "This test verifies that PostgreSQL RLS policies enforce tenant"
echo "isolation at the database engine level using raw SQL queries"
echo "connecting as 'sentinel_app' (NOBYPASSRLS)."
echo ""

if ! command -v docker &> /dev/null; then
    echo "[-] Warning: 'docker' command is not available in PATH."
    echo "    Attempting direct execution against local environment..."
    if command -v pytest &> /dev/null; then
        export PYTHONPATH="${PROJECT_DIR}/backend:${PYTHONPATH:-}"
        cd "${PROJECT_DIR}/backend"
        pytest tests/postgres/ -v
        exit $?
    elif python3 -m pytest --version &> /dev/null; then
        export PYTHONPATH="${PROJECT_DIR}/backend:${PYTHONPATH:-}"
        cd "${PROJECT_DIR}/backend"
        python3 -m pytest tests/postgres/ -v
        exit $?
    else
        echo "[-] Error: Neither Docker nor pytest is available."
        exit 1
    fi
fi

echo "[*] Launching PostGIS test database, running migrations as sentinel_migrator, and executing RLS suite..."
docker compose -f compose.test.yaml down -v --remove-orphans 2>/dev/null || true
docker compose -f compose.test.yaml build
docker compose -f compose.test.yaml up --abort-on-container-exit --exit-code-from test-runner

EXIT_CODE=$?
docker compose -f compose.test.yaml down -v

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "[+] SUCCESS: PostgreSQL RLS tenant isolation verified at database level."
else
    echo ""
    echo "[-] FAILURE: PostgreSQL RLS verification failed."
    exit $EXIT_CODE
fi
