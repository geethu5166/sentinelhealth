#!/usr/bin/env bash
# wait-ready.sh — Wait for all SentinelHealth services to be healthy
set -euo pipefail

MAX_WAIT=120
INTERVAL=3
ELAPSED=0

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

wait_for() {
  local name="$1"
  local check_cmd="$2"
  local start=$ELAPSED

  printf "${YELLOW}⏳ Waiting for %s...${NC}\n" "$name"
  while ! eval "$check_cmd" > /dev/null 2>&1; do
    sleep "$INTERVAL"
    ELAPSED=$((ELAPSED + INTERVAL))
    if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
      printf "${RED}✗ Timed out waiting for %s after %ds${NC}\n" "$name" "$MAX_WAIT"
      exit 1
    fi
  done
  local took=$((ELAPSED - start))
  printf "${GREEN}✓ %s is ready (%ds)${NC}\n" "$name" "$took"
}

echo "═══════════════════════════════════════════"
echo "  SentinelHealth — Waiting for services"
echo "═══════════════════════════════════════════"

wait_for "PostgreSQL" \
  "docker compose exec -T postgres pg_isready -U sentinel -d sentinelhealth"

wait_for "Redis" \
  "docker compose exec -T redis redis-cli ping"

wait_for "Keycloak" \
  "curl -sf http://127.0.0.1:9001/health/ready && curl -sf http://127.0.0.1:8081/realms/sentinelhealth"

wait_for "API" \
  "curl -sf http://localhost:8000/health/live"

wait_for "Nginx" \
  "curl -sf http://localhost:8080/health"

echo ""
printf "${GREEN}═══════════════════════════════════════════${NC}\n"
printf "${GREEN}  All services are ready! (${ELAPSED}s)${NC}\n"
printf "${GREEN}═══════════════════════════════════════════${NC}\n"
echo ""
echo "  Frontend:  http://localhost:8080"
echo "  API:       http://localhost:8080/api/"
echo "  API Docs:  http://localhost:8080/docs"
echo "  Keycloak:  http://localhost:8081"
echo "  Mailpit:   http://localhost:8025"
echo ""
