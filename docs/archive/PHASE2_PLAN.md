# Phase 2: Automation via n8n Workflows — Master Plan v2

## Context

DataPulse Phase 1 is complete: a manually-triggered medallion pipeline (Bronze/Silver/Gold) with a FastAPI analytics API and a Next.js dashboard. **The problem**: every data refresh requires manual CLI commands (`python -m datapulse.bronze.loader`, `dbt run`). There is no scheduling, no file watching, no error notifications, and no pipeline observability. Phase 2 transforms DataPulse into a self-operating data platform using n8n as the orchestration engine, with AI-powered insights via OpenRouter (free tier).

---

## Gap Audit Summary (v1 -> v2 fixes)

| # | Gap | Severity | Fix |
|---|-----|----------|-----|
| 1 | No `networks:` block in docker-compose | MEDIUM | Use default network, remove `networks:` from n8n/redis |
| 2 | API container lacks dbt/data volume mounts | CRITICAL | Add `./dbt`, `./data`, `./migrations` mounts to `api` service |
| 4 | Missing HTTP client dependency | CRITICAL | Add `httpx>=0.27,<1` to pyproject.toml |
| 6 | n8n `WEBHOOK_URL` internal-only | MEDIUM | Set to `http://localhost:5678/` |
| 8 | No RLS on new tables | CRITICAL | Add tenant-scoped RLS to `pipeline_runs`, `quality_checks`, `processed_files` |
| 10 | No OpenRouter key in n8n env | CRITICAL | Pass `OPENROUTER_API_KEY` to n8n container |
| 11 | Phase 2.8 AI-Light missing | CRITICAL | Full design added below |
| 12 | CORS allows only GET | CRITICAL | Expand to `["GET","POST","PATCH"]` |
| 15 | API lacks dbt env vars | CRITICAL | Add `DBT_HOST`, `DBT_PROFILES_DIR`, `POSTGRES_*` to api service |
| 16 | `metadata` JSONB column needed | MEDIUM | Already in migration design |

---

## Sub-Phase Overview

| Phase | Name | Deliverable | Key Services |
|-------|------|-------------|--------------|
| **2.0** | Infra Prep | Fix all gaps, add deps, update docker-compose | docker, pyproject |
| **2.1** | n8n Infrastructure | n8n + Redis in Docker, connected to PG | n8n, redis |
| **2.2** | Pipeline Status Tracking | `pipeline_runs` table + 5 API endpoints | pipeline module |
| **2.3** | Webhook Trigger | On-demand full pipeline via HTTP | executor, n8n workflow |
| **2.4** | File Watcher | Auto-detect new files, trigger pipeline | file-watcher service |
| **2.5** | Data Quality Gates | Row counts, schema drift, null checks | quality module |
| **2.6** | Notifications | Slack/email alerts on success/failure | n8n notification workflows |
| **2.7** | Scheduling + Dashboard | Cron runs, tenant support, pipeline UI | frontend page, cron workflows |
| **2.8** | AI-Light (OpenRouter) | AI summaries, anomaly detection, narratives | n8n + OpenRouter free |

### Dependency Graph

```
2.0 (Infra Prep — fix all gaps)
 |
 v
2.1 (n8n + Redis containers)
 |
 v
2.2 (Pipeline Status Tracking) -----> 2.5 (Quality Gates)
 |                                          |
 v                                          v
2.3 (Webhook Trigger) ------------> 2.6 (Notifications)
 |                                          |
 v                                          v
2.4 (File Watcher)                  2.7 (Scheduling + Dashboard)
                                            |
                                            v
                                    2.8 (AI-Light — OpenRouter)
                                     |-- 2.8.1 AI Pipeline Summary (needs 2.5 + 2.6)
                                     |-- 2.8.2 AI Anomaly Detection (needs 2.5)
                                     |-- 2.8.3 AI Change Narrative (needs 2.5 + 2.7)
```

---

## Sub-Phase 2.0: Infrastructure Prep (Gap Fixes)

### Objective
Fix all critical gaps before any Phase 2 code.

### Changes

**`docker-compose.yml`** — modify `api` service:
```yaml
api:
  environment:
    DATABASE_URL: postgresql://${POSTGRES_USER:-datapulse}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB:-datapulse}
    DBT_HOST: postgres
    DBT_PROFILES_DIR: /app/dbt
    POSTGRES_USER: ${POSTGRES_USER:-datapulse}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    POSTGRES_DB: ${POSTGRES_DB:-datapulse}
  volumes:
    - ./src:/app/src
    - ./dbt:/app/dbt          # NEW — needed for dbt run
    - ./data:/app/data        # NEW — needed for bronze loader
    - ./migrations:/app/migrations  # NEW — needed for migration runner
```

**`pyproject.toml`** — add dependencies:
```
"httpx>=0.27,<1",
"watchdog>=4.0,<5",
```

**`src/datapulse/api/app.py`** — expand CORS:
```python
allow_methods=["GET", "POST", "PATCH"],
```

**`src/datapulse/config.py`** — add new settings:
```python
# n8n
n8n_webhook_url: str = "http://n8n:5678/webhook/"

# OpenRouter
openrouter_api_key: str = ""
openrouter_model: str = "openrouter/free"

# Notifications
slack_webhook_url: str = ""
notification_email: str = ""
```

**`.env.example`** — add:
```ini
# n8n (Phase 2)
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=<choose-a-strong-password>
N8N_ENCRYPTION_KEY=<generate-with: openssl rand -hex 32>

# OpenRouter (Phase 2.8)
OPENROUTER_API_KEY=sk-or-your-key-here
OPENROUTER_MODEL=openrouter/free

# Slack (Phase 2.6)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### Verification
- `docker compose build` succeeds
- `docker compose up api` starts with dbt available: `docker exec datapulse-api dbt --version`

---

## Sub-Phase 2.1: n8n Infrastructure & Connectivity

### Objective
Stand up n8n + Redis as Docker services connected to the existing PostgreSQL database.

### Docker Changes (`docker-compose.yml`)

Add 2 new services (NO `networks:` — use default):

```yaml
n8n:
  image: n8nio/n8n:latest
  container_name: datapulse-n8n
  restart: unless-stopped
  ports:
    - "127.0.0.1:5678:5678"
  environment:
    DB_TYPE: postgresdb
    DB_POSTGRESDB_HOST: postgres
    DB_POSTGRESDB_PORT: 5432
    DB_POSTGRESDB_DATABASE: ${POSTGRES_DB:-datapulse}
    DB_POSTGRESDB_SCHEMA: n8n
    DB_POSTGRESDB_USER: ${POSTGRES_USER:-datapulse}
    DB_POSTGRESDB_PASSWORD: ${POSTGRES_PASSWORD}
    N8N_BASIC_AUTH_ACTIVE: "true"
    N8N_BASIC_AUTH_USER: ${N8N_BASIC_AUTH_USER:-admin}
    N8N_BASIC_AUTH_PASSWORD: ${N8N_BASIC_AUTH_PASSWORD}
    N8N_ENCRYPTION_KEY: ${N8N_ENCRYPTION_KEY}
    WEBHOOK_URL: http://localhost:5678/
    EXECUTIONS_MODE: queue
    QUEUE_BULL_REDIS_HOST: redis
    OPENROUTER_API_KEY: ${OPENROUTER_API_KEY}
    OPENROUTER_MODEL: ${OPENROUTER_MODEL:-openrouter/free}
  volumes:
    - n8n_data:/home/node/.n8n
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_started

redis:
  image: redis:7-alpine
  container_name: datapulse-redis
  restart: unless-stopped
  volumes:
    - redis_data:/data
```

Add to `volumes:`:
```yaml
volumes:
  pgdata:
  pgadmin_data:
  n8n_data:      # NEW
  redis_data:    # NEW
```

### New Files
- `migrations/004_create_n8n_schema.sql` — `CREATE SCHEMA IF NOT EXISTS n8n; GRANT ALL ON SCHEMA n8n TO datapulse;`
- `n8n/workflows/2.1.1_health_check.json` — Cron (5min) pings `GET http://api:8000/health`

### Verification
- `docker compose up -d n8n redis` starts clean
- n8n UI at `http://localhost:5678`
- n8n PostgreSQL node can `SELECT 1` from datapulse DB
- Health check workflow runs successfully

---

## Sub-Phase 2.2: Pipeline Status Tracking & API

### Objective
Create `pipeline_runs` table and FastAPI endpoints to record/query pipeline execution status.

### Database — `migrations/005_create_pipeline_runs.sql`

```sql
CREATE TABLE public.pipeline_runs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       INT NOT NULL DEFAULT 1 REFERENCES bronze.tenants(tenant_id),
  run_type        TEXT NOT NULL,
  status          TEXT NOT NULL DEFAULT 'pending',
  trigger_source  TEXT,
  started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at     TIMESTAMPTZ,
  duration_seconds NUMERIC(10,2),
  rows_loaded     INT,
  error_message   TEXT,
  metadata        JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_pipeline_runs_status ON pipeline_runs(tenant_id, status);
CREATE INDEX idx_pipeline_runs_started ON pipeline_runs(started_at DESC);

-- Tenant-scoped RLS (matches existing pattern)
ALTER TABLE pipeline_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_runs FORCE ROW LEVEL SECURITY;
CREATE POLICY owner_all ON pipeline_runs FOR ALL TO datapulse USING (true) WITH CHECK (true);
CREATE POLICY reader_select ON pipeline_runs FOR SELECT TO datapulse_reader
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
```

### New Python Module — `src/datapulse/pipeline/`

| File | Contents |
|------|----------|
| `__init__.py` | — |
| `models.py` | `PipelineRunCreate`, `PipelineRunUpdate`, `PipelineRunResponse`, `PipelineRunList` (frozen Pydantic) |
| `repository.py` | `create_run()`, `update_run()`, `get_run()`, `list_runs()`, `get_latest_run()` |
| `service.py` | `start_run()`, `update_status()`, `complete_run()`, `fail_run()` |

### New API Routes — `src/datapulse/api/routes/pipeline.py`

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/pipeline/runs` | List runs (paginated, filterable) |
| `GET` | `/api/v1/pipeline/runs/latest` | Latest run |
| `GET` | `/api/v1/pipeline/runs/{run_id}` | Single run detail |
| `POST` | `/api/v1/pipeline/runs` | Create run (used by n8n) |
| `PATCH` | `/api/v1/pipeline/runs/{run_id}` | Update status (used by n8n) |

### Modified Files
- `src/datapulse/api/app.py` — register pipeline router
- `src/datapulse/api/deps.py` — add `get_pipeline_service()` dependency

### Tests
- `tests/test_pipeline_models.py`
- `tests/test_pipeline_repository.py`
- `tests/test_pipeline_service.py`
- `tests/test_pipeline_endpoints.py`

---

## Sub-Phase 2.3: Webhook Trigger & Full Pipeline Execution

### Objective
n8n workflow receives a webhook POST, runs Bronze -> dbt Silver -> dbt Gold, updating `pipeline_runs` at each stage.

### Architecture Decision
n8n calls **FastAPI internal endpoints** (via Docker DNS `http://api:8000`). The API container now has dbt/data mounts (Gap 2 fix), so it can run the full pipeline.

### New Files

**`src/datapulse/pipeline/executor.py`** — orchestrates the full pipeline:
- `execute_bronze(run_id, source_dir, tenant_id)` — calls existing `bronze.loader.run()`
- `execute_dbt_staging(run_id)` — `subprocess.run(["dbt", "run", "--project-dir", "/app/dbt", "--profiles-dir", "/app/dbt", "--models", "staging"])`
- `execute_dbt_marts(run_id)` — `subprocess.run(["dbt", "run", "--project-dir", "/app/dbt", "--profiles-dir", "/app/dbt", "--models", "marts"])`
- Updates `pipeline_runs.status` at each stage

### New Internal API Endpoints (in `pipeline.py`)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/v1/pipeline/trigger` | Create run + call n8n webhook via httpx |
| `POST` | `/api/v1/pipeline/execute/bronze` | Run bronze loader |
| `POST` | `/api/v1/pipeline/execute/dbt-staging` | Run dbt staging |
| `POST` | `/api/v1/pipeline/execute/dbt-marts` | Run dbt marts |

### n8n Workflow — `2.3.1_full_pipeline_webhook.json`

```
Webhook POST /webhook/pipeline-trigger
  -> PATCH status=running
  -> POST http://api:8000/api/v1/pipeline/execute/bronze
  -> PATCH status=bronze_complete
  -> POST http://api:8000/api/v1/pipeline/execute/dbt-staging
  -> PATCH status=silver_complete
  -> POST http://api:8000/api/v1/pipeline/execute/dbt-marts
  -> PATCH status=gold_complete -> success

Error branch at any step:
  -> PATCH status=failed + error_message
```

### Modified Files
- `src/datapulse/config.py` — already has `n8n_webhook_url` from 2.0

### Tests
- `tests/test_pipeline_executor.py` — mock subprocess, verify status flow
- `tests/test_pipeline_trigger_endpoint.py`

---

## Sub-Phase 2.4: File-Based Trigger (Directory Watcher)

### Objective
Auto-detect new Excel/CSV files in the watch directory and trigger the pipeline.

### New Docker Service — `file-watcher`

```yaml
file-watcher:
  build: .
  container_name: datapulse-file-watcher
  restart: unless-stopped
  command: python -m datapulse.watcher
  volumes:
    - ./src:/app/src
    - ./data:/app/data
    - "E:/Data Analysis/sales/RAW FULL:/app/data/raw/sales"
  environment:
    N8N_WEBHOOK_URL: http://n8n:5678/webhook/file-trigger
    WATCH_DIR: /app/data/raw/sales
    DATABASE_URL: postgresql://${POSTGRES_USER:-datapulse}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB:-datapulse}
  depends_on: [n8n, api]
```

### New Python Module — `src/datapulse/watcher/`

| File | Purpose |
|------|---------|
| `__init__.py` | — |
| `__main__.py` | Entry point: start observer |
| `observer.py` | `watchdog` FileSystemEventHandler: on `.xlsx`/`.csv` created -> POST to n8n webhook via httpx |

Logic: debounce 5s, verify file size stable, check SHA-256 hash against `processed_files` table.

### Database — `migrations/006_create_processed_files.sql`

```sql
CREATE TABLE public.processed_files (
  id              SERIAL PRIMARY KEY,
  file_path       TEXT NOT NULL UNIQUE,
  file_hash       TEXT,
  file_size_bytes BIGINT,
  processed_at    TIMESTAMPTZ DEFAULT now(),
  pipeline_run_id UUID REFERENCES pipeline_runs(id),
  tenant_id       INT NOT NULL DEFAULT 1 REFERENCES bronze.tenants(tenant_id)
);

-- RLS
ALTER TABLE processed_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE processed_files FORCE ROW LEVEL SECURITY;
CREATE POLICY owner_all ON processed_files FOR ALL TO datapulse USING (true) WITH CHECK (true);
CREATE POLICY reader_select ON processed_files FOR SELECT TO datapulse_reader
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
```

### n8n Workflows
- `2.4.1_file_trigger.json` — Webhook receives file path -> check duplicates -> trigger pipeline
- `2.4.2_catchup_scanner.json` — Cron (30min) lists files, finds unprocessed, triggers pipeline

### Tests
- `tests/test_watcher.py`
- `tests/test_processed_files.py`

---

## Sub-Phase 2.5: Data Quality Gates

### Objective
Validation checks between pipeline stages: halt on failure, record results.

### Quality Checks

| Check | Stage | Severity | Logic |
|-------|-------|----------|-------|
| Row count > 0 | bronze | error | `COUNT(*)` after load |
| Row delta < 50% | bronze | warning | Compare to last run |
| Schema drift | bronze | error | Compare columns to `COLUMN_MAP` |
| Null rate < 5% | bronze | error | Critical cols: `reference_no`, `date`, `material`, `customer` |
| Dedup effective | silver | warning | `silver_count < bronze_count` |
| Financial signs | silver | warning | `net_amount` signs match `quantity` |
| dbt tests pass | gold | error | `dbt test --models marts` |

### New Files
- `src/datapulse/pipeline/quality.py` — `QualityCheckResult`, `QualityReport`, check functions
- `migrations/007_create_quality_checks.sql`:

```sql
CREATE TABLE public.quality_checks (
  id              SERIAL PRIMARY KEY,
  pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(id),
  tenant_id       INT NOT NULL DEFAULT 1 REFERENCES bronze.tenants(tenant_id),
  stage           TEXT NOT NULL,
  check_name      TEXT NOT NULL,
  passed          BOOLEAN NOT NULL,
  severity        TEXT NOT NULL,
  expected_value  TEXT,
  actual_value    TEXT,
  checked_at      TIMESTAMPTZ DEFAULT now()
);

-- RLS
ALTER TABLE quality_checks ENABLE ROW LEVEL SECURITY;
ALTER TABLE quality_checks FORCE ROW LEVEL SECURITY;
CREATE POLICY owner_all ON quality_checks FOR ALL TO datapulse USING (true) WITH CHECK (true);
CREATE POLICY reader_select ON quality_checks FOR SELECT TO datapulse_reader
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
```

### New API Endpoints
- `GET /api/v1/pipeline/runs/{run_id}/quality` — quality results for a run
- `POST /api/v1/pipeline/execute/quality-check` — run checks for a stage

### n8n Workflow Update
Insert quality gate nodes after each pipeline stage in `2.3.1`:
```
Bronze -> Quality Check -> IF passed? -> dbt Staging -> Quality Check -> IF passed? -> dbt Marts -> Quality Check -> Success
                            |                                           |                            |
                            v                                           v                            v
                          FAIL                                        FAIL                         FAIL
```

### Tests
- `tests/test_quality_checks.py`

---

## Sub-Phase 2.6: Error Handling & Notifications

### Objective
Slack + email alerts on pipeline success, failure, and quality warnings.

### n8n Workflows

| Workflow | Trigger | Action |
|----------|---------|--------|
| `2.6.1_success_notification.json` | Sub-workflow (called on success) | Slack message to `#datapulse-pipeline` |
| `2.6.2_failure_alert.json` | Sub-workflow (called on failure) | Slack `@channel` to `#datapulse-alerts` + email |
| `2.6.3_quality_digest.json` | Cron (daily 18:00) | Daily quality summary digest |
| `2.6.4_global_error_handler.json` | n8n global error handler | Generic alert for any workflow crash |

### Modified Files
- `src/datapulse/config.py` — already has `slack_webhook_url`, `notification_email` from 2.0

---

## Sub-Phase 2.7: Scheduling, Multi-Tenant, Pipeline Dashboard

### Objective
Cron scheduling, tenant_id propagation, and a frontend pipeline status page.

### n8n Workflows
- `2.7.1_daily_scheduled.json` — Cron 02:00 AM daily -> trigger pipeline
- `2.7.2_weekly_rebuild.json` — Cron Sunday 03:00 AM -> `dbt run --full-refresh`

### Multi-Tenant Changes
- `src/datapulse/pipeline/executor.py` — accept + propagate `tenant_id`
- `src/datapulse/bronze/loader.py` — add `--tenant-id` CLI flag
- n8n workflows pass `tenant_id` through all nodes

### Cache Invalidation
- New endpoint: `GET /api/v1/pipeline/last-updated` — frontend polls to refresh SWR

### Frontend — Pipeline Dashboard

**New page:** `/pipeline`

| Component | File | Purpose |
|-----------|------|---------|
| Page | `frontend/src/app/pipeline/page.tsx` | Pipeline status dashboard |
| Loading | `frontend/src/app/pipeline/loading.tsx` | Skeleton |
| Overview | `frontend/src/components/pipeline/pipeline-overview.tsx` | KPI cards (runs, success rate, avg duration) |
| History | `frontend/src/components/pipeline/run-history-table.tsx` | Sortable run list |
| Status Badge | `frontend/src/components/pipeline/run-status-badge.tsx` | Colored status pill |
| Quality | `frontend/src/components/pipeline/quality-details.tsx` | Expandable quality checks |
| Trigger | `frontend/src/components/pipeline/trigger-button.tsx` | Manual trigger button |
| AI Summary | `frontend/src/components/pipeline/ai-summary-card.tsx` | Display AI-generated summary from metadata |

**New hooks:**
- `use-pipeline-runs.ts` — `GET /api/v1/pipeline/runs`
- `use-pipeline-run.ts` — `GET /api/v1/pipeline/runs/{id}`
- `use-last-updated.ts` — cache invalidation signal

**Modified:** `sidebar.tsx` + `constants.ts` — add "Pipeline" nav item

### Tests
- `tests/test_tenant_propagation.py`
- `tests/test_cache_invalidation.py`
- `frontend/e2e/pipeline.spec.ts`

---

## Sub-Phase 2.8: AI-Light with OpenRouter (Free Tier)

### Objective
Add optional AI-generated insights to the pipeline using OpenRouter's free auto-router. All AI features are **non-blocking** — if OpenRouter fails, the pipeline completes normally.

### Configuration

```
Provider:   OpenRouter (free tier)
Model:      openrouter/free (auto-selects best free model)
Endpoint:   https://openrouter.ai/api/v1/chat/completions
API Key:    In .env as OPENROUTER_API_KEY (passed to n8n container)
Rate Limit: 50 req/day (free), 1000/day (with $10 credits)
Cost:       $0.00
```

### 2.8.1: AI Pipeline Summary

**When:** After successful pipeline run completes.

**n8n Nodes:**
1. **Collect Context** — gather rows_loaded, duration, quality results, today's revenue from `metrics_summary`
2. **HTTP Request to OpenRouter:**
   ```json
   {
     "model": "{{ $env.OPENROUTER_MODEL }}",
     "messages": [
       {"role": "system", "content": "You are a data analyst for a pharmacy sales company. Generate concise executive summaries in English. 2-3 sentences max."},
       {"role": "user", "content": "Summarize this pipeline run:\n- Rows loaded: {{rows_loaded}}\n- Duration: {{duration}}s\n- Quality: {{passed}}/{{total}} passed\n- Daily revenue: {{today_net}} EGP\n- MTD: {{mtd_net}} EGP\n- MoM growth: {{mom_growth}}%"}
     ],
     "max_tokens": 200,
     "temperature": 0.3
   }
   ```
3. **Error Handler** — on failure, set `ai_summary = "AI summary unavailable"`
4. **Store** — UPDATE `pipeline_runs.metadata` with `ai_summary`
5. **Include in Slack notification** (Phase 2.6)

**Rate budget:** 1 req/run

### 2.8.2: AI Anomaly Detection

**When:** During quality gates (Phase 2.5), after hardcoded checks pass.

**n8n Nodes:**
1. **Fetch 30-day metrics** from `metrics_summary`
2. **HTTP Request to OpenRouter** — ask to flag anomalies (>2 std deviations), respond as JSON
3. **Parse response** — if `has_anomaly: true`, store in `quality_checks` with `check_name = 'ai_anomaly'`
4. **Error Handler** — skip silently, log `"AI anomaly check skipped"`

**Rate budget:** 1 req/run (total: 2/run)

### 2.8.3: AI Data Change Narrative

**When:** After gold layer refresh (dbt marts complete).

**n8n Nodes:**
1. **Fetch current vs previous month** from `agg_sales_monthly`
2. **HTTP Request to OpenRouter** — describe changes in business terms
3. **Store** — UPDATE `pipeline_runs.metadata` with `change_narrative`
4. **Error Handler** — fallback to `"Change narrative unavailable"`

**Rate budget:** 1 req/run (total: 3/run, ~6/day = well within 50 free)

### Fallback Strategy (all 2.8.x)

- HTTP timeout: 30 seconds
- n8n retry: 1 retry, 5-second wait
- On error: merge back to main flow with fallback string
- Rate limit tracking: check `X-RateLimit-Remaining` header, skip AI if < 5 remaining

### n8n Workflow Files
- `n8n/workflows/2.8.1_ai_pipeline_summary.json`
- `n8n/workflows/2.8.2_ai_anomaly_detection.json`
- `n8n/workflows/2.8.3_ai_change_narrative.json`

---

## Complete File Inventory

### New Python Files (11)
```
src/datapulse/pipeline/__init__.py
src/datapulse/pipeline/models.py
src/datapulse/pipeline/repository.py
src/datapulse/pipeline/service.py
src/datapulse/pipeline/executor.py
src/datapulse/pipeline/quality.py
src/datapulse/api/routes/pipeline.py
src/datapulse/watcher/__init__.py
src/datapulse/watcher/__main__.py
src/datapulse/watcher/observer.py
```

### Modified Python Files (4)
```
src/datapulse/config.py          — n8n_webhook_url, openrouter_*, slack_webhook_url, notification_email
src/datapulse/api/app.py         — register pipeline router, expand CORS to GET/POST/PATCH
src/datapulse/api/deps.py        — add get_pipeline_service()
src/datapulse/bronze/loader.py   — add tenant_id parameter
```

### Migrations (4)
```
migrations/004_create_n8n_schema.sql
migrations/005_create_pipeline_runs.sql      (with RLS + metadata JSONB)
migrations/006_create_processed_files.sql    (with RLS)
migrations/007_create_quality_checks.sql     (with RLS)
```

### n8n Workflows (13)
```
n8n/workflows/2.1.1_health_check.json
n8n/workflows/2.3.1_full_pipeline_webhook.json
n8n/workflows/2.4.1_file_trigger.json
n8n/workflows/2.4.2_catchup_scanner.json
n8n/workflows/2.6.1_success_notification.json
n8n/workflows/2.6.2_failure_alert.json
n8n/workflows/2.6.3_quality_digest.json
n8n/workflows/2.6.4_global_error_handler.json
n8n/workflows/2.7.1_daily_scheduled.json
n8n/workflows/2.7.2_weekly_rebuild.json
n8n/workflows/2.8.1_ai_pipeline_summary.json
n8n/workflows/2.8.2_ai_anomaly_detection.json
n8n/workflows/2.8.3_ai_change_narrative.json
```

### Frontend New Files (11)
```
frontend/src/app/pipeline/page.tsx
frontend/src/app/pipeline/loading.tsx
frontend/src/components/pipeline/pipeline-overview.tsx
frontend/src/components/pipeline/run-history-table.tsx
frontend/src/components/pipeline/run-status-badge.tsx
frontend/src/components/pipeline/quality-details.tsx
frontend/src/components/pipeline/trigger-button.tsx
frontend/src/components/pipeline/ai-summary-card.tsx
frontend/src/hooks/use-pipeline-runs.ts
frontend/src/hooks/use-pipeline-run.ts
frontend/src/hooks/use-last-updated.ts
```

### Frontend Modified Files (2)
```
frontend/src/components/layout/sidebar.tsx  — add Pipeline nav
frontend/src/lib/constants.ts               — add pipeline nav entry
```

### Tests (13+)
```
tests/test_pipeline_models.py
tests/test_pipeline_repository.py
tests/test_pipeline_service.py
tests/test_pipeline_endpoints.py
tests/test_pipeline_executor.py
tests/test_pipeline_trigger_endpoint.py
tests/test_watcher.py
tests/test_processed_files.py
tests/test_quality_checks.py
tests/test_notification_formatting.py
tests/test_tenant_propagation.py
tests/test_cache_invalidation.py
frontend/e2e/pipeline.spec.ts
```

### Config Changes
```
docker-compose.yml  — fix api mounts + env, add n8n + redis + file-watcher, add volumes
pyproject.toml      — add httpx, watchdog
.env.example        — add N8N_*, OPENROUTER_*, SLACK_WEBHOOK_URL
.env                — actual values (gitignored, never committed)
```

---

## Execution Strategy — Sub-Agents

Each sub-phase uses **parallel sub-agents** for maximum speed:

| Sub-Phase | Agent 1 | Agent 2 | Agent 3 |
|-----------|---------|---------|---------|
| **2.0** | Docker + pyproject fixes | Config + CORS fixes | .env.example updates |
| **2.1** | Docker services + migration | n8n workflow JSON | Verification script |
| **2.2** | Pipeline module (models + repo + service) | API routes + deps | Tests |
| **2.3** | Executor module | API endpoints + n8n workflow | Tests |
| **2.4** | Watcher module + Docker service | Migration + n8n workflows | Tests |
| **2.5** | Quality module + migration | API endpoints + n8n updates | Tests |
| **2.6** | n8n notification workflows (4) | Config updates | — |
| **2.7** | Scheduling workflows + tenant changes | Frontend dashboard (all components) | Frontend hooks + E2E tests |
| **2.8** | AI summary workflow (2.8.1) | AI anomaly workflow (2.8.2) | AI narrative workflow (2.8.3) |

---

---

## Phase 3 Decision: LangGraph CANCELLED

**Decision date:** 2026-03-28

**Original plan:** Phase 3 was "AI-powered analysis via LangGraph" — conversational analytics, multi-step reasoning, self-correcting SQL queries.

**Decision:** Phase 3 is cancelled. Phase 2.8 (AI-Light) replaces it entirely.

**Reasons:**
1. **No budget for paid AI APIs** — OpenRouter free tier only (~50 req/day, rate-limited). LangGraph and Claude Agent SDK both require reliable, fast, paid APIs with strong tool_use support. Free models have inconsistent tool calling and can't handle agent loops.
2. **n8n + OpenRouter free covers 80% of value** — dbt aggregations already compute MoM growth, YoY trends, rankings. The AI model just narrates pre-computed numbers, not discovers them.
3. **Architecture: "smart narrator, not smart analyst"** — AI summaries are generated once per pipeline run and stored in `pipeline_runs.metadata`. No real-time queries, no conversational memory needed.
4. **Fewer dependencies** — no LangChain/LangGraph dependency tree. Just HTTP calls from n8n to OpenRouter.
5. **Graceful degradation** — if OpenRouter fails or rate-limits, pipeline completes normally with fallback text.

**What's preserved:**
- AI pipeline summary (2.8.1)
- AI anomaly detection (2.8.2)
- AI change narrative (2.8.3)
- All stored in `pipeline_runs.metadata` JSONB
- Displayed in frontend `ai-summary-card.tsx`

**What's deferred (if paid API becomes available later):**
- Conversational "ask questions about my data"
- Multi-step investigation chains
- Self-correcting SQL generation
- Dynamic tool selection
- If needed, use Claude Agent SDK (not LangGraph) — simpler, fewer dependencies

---

## Verification Plan

After each sub-phase:
1. `docker compose up -d --build` — all services start
2. `pytest tests/ -v --cov=src/datapulse --cov-fail-under=80` — tests pass
3. `docker compose exec api curl http://localhost:8000/health` — API healthy
4. n8n UI at `http://localhost:5678` — workflows visible and executable
5. After 2.7: `npx playwright test` for frontend E2E
6. After 2.8: trigger pipeline, verify AI summary appears in Slack + dashboard
