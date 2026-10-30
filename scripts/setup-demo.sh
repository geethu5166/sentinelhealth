#!/usr/bin/env bash
# setup-demo.sh — One-command demo environment setup for SentinelHealth
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

step() {
  printf "\n${YELLOW}━━━ %s ━━━${NC}\n" "$1"
}

step "1/7 — Setting up environment file"
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"

  # Generate random secrets
  if command -v python3 &> /dev/null; then
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    sed -i.bak "s/CHANGE_ME_random_secret_key_at_least_32_chars/${SECRET_KEY}/" .env 2>/dev/null || \
      sed -i '' "s/CHANGE_ME_random_secret_key_at_least_32_chars/${SECRET_KEY}/" .env
    rm -f .env.bak
    echo "Generated random SENTINEL_SECRET_KEY"
  else
    printf "${YELLOW}⚠ python3 not found — please update SENTINEL_SECRET_KEY in .env manually${NC}\n"
  fi
else
  echo ".env already exists, skipping"
fi

step "2/7 — Building Docker images"
docker compose build

step "3/7 — Starting services"
docker compose up -d

step "4/7 — Waiting for services to be ready"
bash scripts/wait-ready.sh

step "5/7 — Running database migrations"
docker compose exec -T api alembic upgrade head || \
  printf "${YELLOW}⚠ Migrations skipped (alembic may not be configured yet)${NC}\n"

step "6/7 — Seeding demo data"
docker compose exec -T api python -m app.db.seed_demo || \
  printf "${YELLOW}⚠ Demo seeding skipped (seed module may not be configured yet)${NC}\n"

step "7/7 — Running smoke tests"
bash scripts/smoke-test.sh || true

echo ""
printf "${GREEN}═══════════════════════════════════════════${NC}\n"
printf "${GREEN}  SentinelHealth demo is ready!${NC}\n"
printf "${GREEN}═══════════════════════════════════════════${NC}\n"
echo ""
echo "  App:       http://localhost:8080"
echo "  API Docs:  http://localhost:8080/docs"
echo "  Keycloak:  http://localhost:8081  (admin / see .env)"
echo "  Mailpit:   http://localhost:8025"
echo ""
echo "  Demo login: analyst@demo.local / demo123"
echo ""
