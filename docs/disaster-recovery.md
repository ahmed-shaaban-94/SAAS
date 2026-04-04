# DataPulse Disaster Recovery Runbook

## Recovery Objectives

| Metric | Target | Current |
|--------|--------|---------|
| **RTO** (Recovery Time Objective) | < 30 minutes | ~15 min (restore + dbt rebuild) |
| **RPO** (Recovery Point Objective) | < 24 hours | Daily pg_dump backups |

## Backup Strategy

### Automated Daily Backups

```bash
# Manual backup
make backup

# Cron job (daily at 2 AM)
0 2 * * * cd /path/to/SAAS && ./scripts/backup.sh >> /var/log/datapulse-backup.log 2>&1
```

- **Format**: `pg_dump --format=custom --compress=6`
- **Location**: `./backups/datapulse_YYYYMMDD_HHMMSS.sql.gz`
- **Retention**: 7 days (configurable via `BACKUP_RETENTION_DAYS`)
- **Estimated size**: ~50-100 MB compressed for 2.27M rows

### What Is Backed Up

| Data | Included | Notes |
|------|----------|-------|
| bronze.sales (2.27M rows) | YES | Full raw data |
| bronze.tenants | YES | Tenant config + billing |
| All public.* tables | YES | Pipeline runs, targets, alerts, audit |
| dbt models (silver/gold) | NO | Rebuilt from bronze via `make dbt` |
| Redis cache | NO | Regenerated automatically |
| n8n workflows | Partial | Stored in PostgreSQL n8n schema |
| Uploaded Excel/CSV files | NO | Store separately in object storage |

### Backup Verification

Verify the latest backup weekly:

```bash
# List recent backups
ls -lh backups/datapulse_*.sql.gz

# Test restore on a throwaway database
docker exec datapulse-db pg_restore \
    --list backups/datapulse_latest.sql.gz | head -20
```

## Restore Procedures

### Scenario 1: Full Database Restore

**When**: Database corruption, accidental DROP, or migration failure.

```bash
# 1. Stop application services (keep postgres running)
docker compose stop api frontend celery-worker n8n

# 2. Restore from backup
./scripts/restore.sh backups/datapulse_YYYYMMDD_HHMMSS.sql.gz

# 3. Run migrations (in case backup is older than latest migration)
docker compose run --rm prestart

# 4. Rebuild dbt models
make dbt

# 5. Restart services
docker compose up -d
```

**Estimated time**: 10-15 minutes.

### Scenario 2: Tenant Data Recovery

**When**: Accidental deletion of tenant data.

```bash
# 1. Identify the tenant_id
SELECT tenant_id, tenant_name FROM bronze.tenants;

# 2. Restore to a temporary database
docker exec datapulse-db createdb datapulse_restore
docker exec datapulse-db pg_restore -U datapulse -d datapulse_restore /tmp/backup.sql.gz

# 3. Extract tenant data
docker exec datapulse-db psql -U datapulse -d datapulse_restore -c "
    COPY (SELECT * FROM bronze.sales WHERE tenant_id = <ID>) TO STDOUT WITH CSV HEADER
" > tenant_data.csv

# 4. Import into production
docker exec datapulse-db psql -U datapulse -d datapulse -c "
    COPY bronze.sales FROM STDIN WITH CSV HEADER
" < tenant_data.csv

# 5. Clean up
docker exec datapulse-db dropdb datapulse_restore
```

### Scenario 3: Pipeline Rollback

**When**: Bad data loaded into bronze.

```bash
# 1. Check pipeline run history
curl -s http://localhost:8000/api/v1/pipeline/runs | python -m json.tool

# 2. Delete the bad pipeline run's data
docker exec datapulse-db psql -U datapulse -d datapulse -c "
    DELETE FROM bronze.sales
    WHERE created_at > '<bad_run_timestamp>'
    AND tenant_id = <tenant_id>;
"

# 3. Rebuild dbt
make dbt
```

### Scenario 4: Complete Infrastructure Rebuild

**When**: Server failure, moving to new host.

```bash
# 1. On new server
git clone https://github.com/ahmed-shaaban-94/SAAS.git
cd SAAS
cp .env.example .env  # Configure with production values

# 2. Start infrastructure
docker compose up -d postgres redis

# 3. Wait for postgres healthy
docker compose exec postgres pg_isready

# 4. Restore database
./scripts/restore.sh <backup-file>

# 5. Start all services
docker compose up -d
```

**Estimated time**: 20-30 minutes.

## Encryption

| Layer | Status | Notes |
|-------|--------|-------|
| **In transit** | Cloudflare TLS | Full mode with origin cert |
| **At rest (DB)** | Docker volume | Enable LUKS/dm-crypt on host for encryption |
| **At rest (backups)** | Not encrypted | Consider `gpg --symmetric` for offsite backups |

## Monitoring

Set up alerts for:

- [ ] Backup script exit code (Slack/email on failure)
- [ ] Backup file size (alert if < 10MB — likely corrupt)
- [ ] Database disk usage (alert at 80% capacity)
- [ ] PostgreSQL replication lag (if read replicas added later)

## Future Improvements

1. **WAL archiving + PITR**: Enable `archive_mode = on` in postgresql.conf for point-in-time recovery
2. **Object storage**: Ship backups to S3/Spaces for offsite durability
3. **Read replica**: Add streaming replication for high availability
4. **Managed database**: Migrate to DigitalOcean Managed PostgreSQL ($15/mo) for automated backups + PITR
