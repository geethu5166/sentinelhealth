# SentinelHealth

> **⚠️ PROTOTYPE — NOT FOR PRODUCTION USE**
>
> This is a hackathon prototype. It uses demo credentials, self-signed tokens,
> and synthetic data. Do **not** deploy to production or use with real health data
> without a full security audit, HIPAA/DISHA compliance review, and proper
> infrastructure hardening.

---

**SentinelHealth** is an integrated occupational-and-public-health surveillance
platform designed for the Indian context. It ingests environmental, workplace,
and health event data; applies privacy-preserving aggregation; and surfaces
actionable insights through role-based dashboards with geospatial and temporal
analytics.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Nginx :8080                          │
│                    (reverse proxy)                           │
├──────────────────────┬──────────────────────────────────────┤
│  Frontend (React)    │  API (FastAPI)  :8000                │
│  Vite :5173          │  ├── /api/v1/...                     │
│                      │  ├── /health/live                    │
│                      │  └── /health/ready                   │
├──────────────────────┴──────────────────────────────────────┤
│         Celery Worker + Beat  (background tasks)            │
├─────────────────┬──────────────────┬────────────────────────┤
│  PostgreSQL     │  Redis           │  Keycloak :8081        │
│  + PostGIS      │  (cache/broker)  │  (identity provider)  │
│  :5433 (local)  │  :6380 (local)   │                        │
├─────────────────┴──────────────────┴────────────────────────┤
│                     Mailpit :8025                           │
│                  (local email testing)                       │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

| Tool             | Version   | Notes                        |
|------------------|-----------|------------------------------|
| Docker           | 24+       | With Compose V2 (`docker compose`) |
| Docker Compose   | 2.20+     | Bundled with Docker Desktop  |
| Node.js          | 20+       | For frontend development     |
| Python           | 3.12+     | For backend development      |
| GNU Make         | 3.8+      | Optional, for `make` targets |

## Quick Start

### One-command setup

```bash
bash scripts/setup-demo.sh
```

### Step-by-step

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Build all images
docker compose build

# 3. Start all services
docker compose up -d

# 4. Wait for everything to be ready
bash scripts/wait-ready.sh

# 5. Run database migrations
docker compose exec api alembic upgrade head

# 6. Seed demo data
docker compose exec api python -m app.db.seed_demo

# 7. Run smoke tests
bash scripts/smoke-test.sh
```

Then open **http://localhost:8080** in your browser.

## Default Ports

| Service    | URL                          | Binding       | Purpose                  |
|------------|------------------------------|---------------|--------------------------|
| Nginx      | http://localhost:8080         | 0.0.0.0:8080  | Main entry point         |
| Keycloak   | http://localhost:8081         | 0.0.0.0:8081  | Identity provider admin  |
| Mailpit    | http://localhost:8025         | 0.0.0.0:8025  | Email testing UI         |
| API        | http://localhost:8000         | 127.0.0.1     | Direct API access (dev)  |
| PostgreSQL | localhost:5433               | 127.0.0.1     | Direct DB access (dev)   |
| Redis      | localhost:6380               | 127.0.0.1     | Direct Redis access (dev)|
| SMTP       | localhost:1025               | 127.0.0.1     | Mailpit SMTP intake      |

> Admin-only services (API, PostgreSQL, Redis, SMTP) are bound to `127.0.0.1`
> and are not accessible from other machines on the network.

## Demo Users

All demo users use password: **`demo123`**

| Email                   | Role                        | Access Level                    |
|-------------------------|-----------------------------|---------------------------------|
| analyst@demo.local      | public_health_analyst       | Public health dashboards        |
| ohanalyst@demo.local    | occupational_health_analyst | Occupational health data        |
| safety@demo.local       | workplace_safety_manager    | Safety compliance & reporting   |
| steward@demo.local      | data_steward                | Data quality & governance       |
| privacy@demo.local      | privacy_officer             | Privacy policies & suppression  |
| admin@demo.local        | platform_admin              | Full platform access            |
| regulator@demo.local    | regulator                   | Read-only compliance reports    |

## Make Targets

```
make help              Show all available targets
make setup-demo        Initial setup: copy env, build images
make up                Start all services
make down              Stop all services
make down-clean        Stop and remove all volumes
make migrate           Run database migrations
make seed-demo         Seed synthetic demo data
make smoke             Run smoke tests
make test              Run all tests (backend + frontend)
make test-backend      Run backend tests only
make test-frontend     Run frontend tests only
make lint              Run all linters
make replay            Run a replay scenario
make logs              Show all service logs
make logs-api          Show API logs
make logs-worker       Show worker logs
make status            Show service status
make db-shell          Open PostgreSQL shell
make redis-cli         Open Redis CLI
```

## Feature Status

| Feature                           | Status       | Notes                                    |
|-----------------------------------|--------------|------------------------------------------|
| Docker Compose dev stack          | ✅ Done      | All services with health checks          |
| Keycloak RBAC with 7 roles       | ✅ Done      | PKCE + audience validation               |
| PostGIS geospatial database      | ✅ Done      | PostgreSQL 17 + PostGIS 3.4              |
| Celery task queue                 | ✅ Done      | Worker + Beat scheduler                  |
| Nginx reverse proxy              | ✅ Done      | Security headers, WebSocket support      |
| Email testing (Mailpit)          | ✅ Done      | SMTP capture for dev                     |
| Privacy-preserving aggregation    | 🔨 In Progress | K-anonymity suppression configured     |
| Geospatial dashboards            | 🔨 In Progress | Frontend components                    |
| Replay/scenario engine           | 🔨 In Progress | CLI runner scaffolded                  |
| FHIR data ingestion              | 📋 Planned   | HL7 FHIR R4 adapter                     |
| Real-time alerting               | 📋 Planned   | WebSocket + push notifications           |
| PDF/Excel report export          | 📋 Planned   | Celery task-based generation             |
| Audit logging                    | 📋 Planned   | Immutable event log                      |
| Production Kubernetes manifests  | ⏳ Deferred  | Out of hackathon scope                   |
| HIPAA/DISHA compliance hardening | ⏳ Deferred  | Requires security audit                  |

## Known Limitations

1. **Not production-ready** — Demo credentials, no TLS, no WAF, no rate limiting
2. **Keycloak uses H2 in dev mode** — Data is ephemeral; realm is re-imported on restart
3. **No database backups** — PostgreSQL volume is local-only
4. **Synthetic data only** — No real patient or workplace health data
5. **Single-node only** — No clustering, replication, or HA configuration
6. **No CI/CD pipeline** — Tests run locally via `make test`

## Project Structure

```
sentinelhealth/
├── backend/              # FastAPI application
│   ├── app/              # Application package
│   ├── tests/            # Backend tests
│   ├── Dockerfile        # Multi-stage Python build
│   └── pyproject.toml    # Python dependencies
├── frontend/             # React + Vite application
│   ├── src/              # Frontend source
│   ├── Dockerfile        # Multi-stage Node build
│   └── package.json      # Node dependencies
├── infra/                # Infrastructure configs
│   ├── keycloak/         # Realm export
│   └── nginx/            # Reverse proxy config
├── scripts/              # Automation scripts
│   ├── setup-demo.sh     # One-command setup
│   ├── wait-ready.sh     # Service readiness waiter
│   └── smoke-test.sh     # Basic health checks
├── compose.yaml          # Docker Compose stack
├── Makefile              # Developer commands
├── .env.example          # Environment template
└── README.md             # This file
```

## License

Licensed under the [Apache License 2.0](LICENSE).

Copyright 2024 SentinelHealth Contributors.

---

*Built for the Hack2Skills hackathon.*
