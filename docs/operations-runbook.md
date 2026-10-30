# SentinelHealth Operations Runbook

## 1. System Health & Diagnostics
Check service readiness locally or in staging:
```bash
# Check API liveness & readiness
curl -f http://localhost:8080/health/live
curl -f http://localhost:8080/health/ready

# Check Docker Compose status
docker compose ps
```

Expected readiness output:
```json
{
  "status": "ready",
  "checks": {
    "database": true,
    "redis": true
  }
}
```

---

## 2. Ingestion & Quality Failures
If an upstream connector reports stale or invalid records:
1. Check ingestion run logs:
   ```bash
   docker compose exec api python -m app.ingestion.diagnose
   ```
2. Verify if the upstream provider format changed. Look for `CONTRACT_VIOLATION` in `ingestion_errors`.
3. If the environmental feed goes down, the system preserves health anomaly detection but transitions alerts to `uncorroborated_health_anomaly` or `insufficient_data`.

---

## 3. Database Maintenance & Backup/Restore
```bash
# Backup PostgreSQL database
docker compose exec postgres pg_dump -U sentinel sentinelhealth > backup_$(date +%Y%m%d).sql

# Restore PostgreSQL database
docker compose exec -T postgres psql -U sentinel -d sentinelhealth < backup_20261030.sql

# Run database migrations
docker compose exec api alembic upgrade head
```

