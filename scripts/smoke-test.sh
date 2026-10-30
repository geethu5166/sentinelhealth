#!/usr/bin/env bash
# smoke-test.sh — Quick smoke tests for SentinelHealth services
set -uo pipefail

BASE_URL="http://localhost:8080"
KEYCLOAK_URL="http://localhost:8081"
MAILPIT_URL="http://localhost:8025"

PASS=0
FAIL=0

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

check() {
  local name="$1"
  local url="$2"
  local expected_code="${3:-200}"

  local code
  code=$(curl -sf -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || echo "000")

  if [ "$code" = "$expected_code" ]; then
    printf "${GREEN}✓ PASS${NC}  %-35s (HTTP %s)\n" "$name" "$code"
    PASS=$((PASS + 1))
  else
    printf "${RED}✗ FAIL${NC}  %-35s (HTTP %s, expected %s)\n" "$name" "$code" "$expected_code"
    FAIL=$((FAIL + 1))
  fi
}

echo "═══════════════════════════════════════════"
echo "  SentinelHealth — Smoke Tests"
echo "═══════════════════════════════════════════"
echo ""

check "API Liveness"            "${BASE_URL}/health/live"
check "API Readiness"           "${BASE_URL}/health/ready"
check "Frontend loads"          "${BASE_URL}/"
check "OpenAPI spec"            "${BASE_URL}/openapi.json"
check "API docs"                "${BASE_URL}/docs"
check "Keycloak realm"          "${KEYCLOAK_URL}/realms/sentinelhealth"
check "Keycloak OIDC config"    "${KEYCLOAK_URL}/realms/sentinelhealth/.well-known/openid-configuration"
check "Mailpit web UI"          "${MAILPIT_URL}/"

echo ""
echo "═══════════════════════════════════════════"
TOTAL=$((PASS + FAIL))
printf "  Results: ${GREEN}%d passed${NC}, ${RED}%d failed${NC}, %d total\n" "$PASS" "$FAIL" "$TOTAL"
echo "═══════════════════════════════════════════"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
