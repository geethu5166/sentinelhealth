.PHONY: help setup-demo up down down-clean migrate seed-demo smoke test test-backend test-frontend lint replay logs logs-api logs-worker status db-shell redis-cli

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup-demo: ## Initial setup: copy env, build images
	@test -f .env || cp .env.example .env
	@echo "Generating local demo credentials..."
	@python3 -c "import secrets; print(f'SENTINEL_SECRET_KEY={secrets.token_urlsafe(32)}')" >> .env.local 2>/dev/null || true
	docker compose build

up: ## Start all services
	docker compose up -d
	@echo "Waiting for services to be ready..."
	@bash scripts/wait-ready.sh

down: ## Stop all services
	docker compose down

down-clean: ## Stop and remove volumes
	docker compose down -v

migrate: ## Run database migrations
	docker compose exec api alembic upgrade head

seed-demo: ## Seed synthetic demo data
	docker compose exec api python -m app.db.seed_demo

smoke: ## Run smoke tests
	@bash scripts/smoke-test.sh

test: ## Run all tests
	docker compose exec api pytest tests/ -v --tb=short
	cd frontend && npm test -- --run

test-backend: ## Run backend tests only
	docker compose exec api pytest tests/ -v --tb=short

test-frontend: ## Run frontend tests only
	cd frontend && npm test -- --run

lint: ## Run all linters
	docker compose exec api ruff check app/
	docker compose exec api mypy app/ --ignore-missing-imports
	cd frontend && npm run lint

replay: ## Run a replay scenario (SCENARIO=heat-gradual)
	docker compose exec api python -m app.replay.runner --scenario=$(SCENARIO)

logs: ## Show service logs
	docker compose logs -f --tail=100

logs-api: ## Show API logs
	docker compose logs -f api

logs-worker: ## Show worker logs
	docker compose logs -f worker

status: ## Show service status
	docker compose ps

db-shell: ## Open database shell
	docker compose exec postgres psql -U sentinel -d sentinelhealth

redis-cli: ## Open Redis CLI
	docker compose exec redis redis-cli
