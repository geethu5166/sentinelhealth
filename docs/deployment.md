# SentinelHealth Deployment Guide: Local & AWS Pilot

## Operational Acceptance Environment Snapshot
- **Repository Commit**: `73a5c4ab3e2a59e67372a921c30667f95c7809ec`
- **Database Engine**: PostgreSQL 18.0 with PostGIS 3.6.4 extension
- **Database Network Binding**: `listen_addresses = 'localhost,127.0.0.1'` (port 5433)
- **Database Migration Revision**: `001_initial_schema` (applies all tables, invoker-security views, RLS policies, and unique idempotency constraints)
- **Application Roles**:
  - `sentinel_migrator`: DDL owner, sets up schemas and grants table permissions
  - `sentinel_app`: Runtime application role configured with `NOBYPASSRLS`
- **Backend Runtime**: Python 3.14.7 (WSL Kali) / Python 3.11.9 (Windows Host)
- **Frontend Runtime**: Node.js v22.12.0, Vite 5.4.21, React 18.3.1, Vitest 2.1.9

## 1. Local Development (Docker Compose)
Prerequisites: Docker Engine 24+, Docker Compose v2.20+, 4GB available RAM.

```bash
# 1. Clone & Setup
git clone <repo-url> sentinelhealth
cd sentinelhealth
cp .env.example .env

# 2. Start stack
make up

# 3. Apply database migrations
make migrate

# 4. Seed demonstration dataset
make seed-demo

# 5. Execute smoke tests
make smoke
```

Access Points:
- Web Application: `http://localhost:8080`
- API OpenAPI Docs: `http://localhost:8080/docs`
- Keycloak Identity: `http://localhost:8081`
- Mailpit Email UI: `http://localhost:8025`

---

## 2. AWS Pilot Deployment Architecture

```mermaid
flowchart TD
    subgraph Internet["Public Ingress"]
        ALB["Application Load Balancer\n(HTTPS TLS 1.3)"]
    end

    subgraph VPC["Private VPC (Multi-AZ)"]
        subgraph Fargate["ECS Fargate Services"]
            API_TASK["API Service\n(FastAPI / Python 3.12)"]
            WORKER_TASK["Worker Service\n(Celery)"]
            BEAT_TASK["Scheduler\n(Single Celery Beat)"]
        end

        subgraph Data["Private Data Subnet"]
            RDS["Amazon RDS PostgreSQL 17\n+ PostGIS 3.4 (Multi-AZ)"]
            REDIS["ElastiCache Redis 7\n(Private cluster)"]
            S3["Amazon S3 Bucket\n(KMS Encrypted Exports)"]
        end
    end

    ALB --> API_TASK
    API_TASK --> RDS
    API_TASK --> REDIS
    API_TASK --> S3
    WORKER_TASK --> RDS
    WORKER_TASK --> REDIS
    BEAT_TASK --> REDIS
```

### AWS Pilot Cost Worksheet (Monthly Estimate)
| Component | Specification | Estimated Monthly Cost |
|---|---|---|
| **ECS Fargate (API + Workers)** | 3 tasks × 0.5 vCPU, 1GB RAM | ~$35.00 |
| **RDS PostgreSQL + PostGIS** | db.t4g.medium, 50GB gp3 storage | ~$65.00 |
| **ElastiCache Redis** | cache.t4g.micro | ~$15.00 |
| **Application Load Balancer** | 1 ALB with standard LCU traffic | ~$22.00 |
| **NAT Gateway** | 1 single-AZ NAT for outbound feeds | ~$32.00 |
| **S3 + CloudWatch + Secrets Manager** | Encrypted exports, structured logs | ~$12.00 |
| **Total Estimated Pilot Cost** | | **~$181.00 / month** |

