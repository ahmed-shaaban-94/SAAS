---
name: add-migration
description: "Create a new idempotent SQL migration with RLS. Usage: /add-migration <description>"
tools: [Read, Write, Edit, Bash, Glob, Grep]
---

You are creating a new PostgreSQL migration for DataPulse. Follow these steps exactly:

## Input
Parse the user's request for:
- **What** to create/alter (table, column, index, policy)
- **Schema** (bronze, public, public_staging, public_marts)
- **Whether tenant_id and RLS are needed** (yes for any data table)

## Steps

### 1. Determine next migration number
```bash
ls /home/user/SAAS/migrations/*.sql | sort | tail -1
```
Use the next sequential number (e.g., if last is `011_`, use `012_`).

### 2. Create migration file
Create at `migrations/<NNN>_<description>.sql`:

```sql
-- Migration: <description>
-- Date: <today>

BEGIN;

-- Always idempotent (IF NOT EXISTS / IF EXISTS)
CREATE TABLE IF NOT EXISTS <schema>.<table> (
    id SERIAL PRIMARY KEY,
    -- columns...
    tenant_id TEXT NOT NULL DEFAULT current_setting('app.tenant_id', true),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- RLS (required for any table with tenant_id)
ALTER TABLE <schema>.<table> ENABLE ROW LEVEL SECURITY;
ALTER TABLE <schema>.<table> FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON <schema>.<table>;
CREATE POLICY tenant_isolation ON <schema>.<table>
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true));

-- Indexes (if needed)
CREATE INDEX IF NOT EXISTS idx_<table>_<col> ON <schema>.<table> (<col>);

-- Grants for read-only role (if needed)
GRANT SELECT ON <schema>.<table> TO datapulse_readonly;

COMMIT;
```

### Rules
- **Always wrap in BEGIN/COMMIT** (transactional)
- **Always idempotent**: `IF NOT EXISTS`, `IF EXISTS`, `DROP ... IF EXISTS` before `CREATE`
- **Always include tenant_id** for data tables
- **Always add RLS** with `FORCE ROW LEVEL SECURITY`
- **Use SERIAL** for auto-increment, **UUID** for distributed IDs
- **Financial columns**: `NUMERIC(18,4)` — never `FLOAT`
- **Timestamps**: `TIMESTAMPTZ` — never `TIMESTAMP`

### 3. Validate the migration
```bash
docker exec datapulse-db psql -U datapulse -d datapulse -f /dev/stdin < /home/user/SAAS/migrations/<NNN>_<description>.sql
```

### 4. Verify
```bash
docker exec datapulse-db psql -U datapulse -d datapulse -c "\d <schema>.<table>"
docker exec datapulse-db psql -U datapulse -d datapulse -c "SELECT polname FROM pg_policy WHERE polrelid = '<schema>.<table>'::regclass"
```

### 5. Report
Show:
- File created with full path
- Table structure
- RLS policy confirmed
- Any issues
