# DataPulse — Remaining Tasks Handoff

> Generated: 2026-03-28
> Last commit: `37c5f63` on `main` — Phase 2.5/2.6/2.7

---

## What's DONE (committed + pushed)

| Phase | Status | Summary |
|-------|--------|---------|
| 2.0 Infra prep | DONE | API volumes, deps, config, CORS |
| 2.1 n8n + Redis | DONE | Docker infrastructure, health check workflow |
| 2.2 Pipeline tracking | DONE | pipeline_runs table, CRUD API, 53 tests |
| 2.3 Webhook trigger | DONE | executor module, trigger + execute endpoints, n8n workflow |
| 2.5 Quality gates | DONE | 7 check functions, migration 007, repo/service, 2 API endpoints, n8n gate nodes, 79 tests |
| 2.6 Notifications | DONE | 4 n8n sub-workflows (success/failure/digest/global error), Slack integration |
| 2.7 Pipeline dashboard | DONE | /pipeline page, 5 components, 3 hooks, E2E tests |

---

## MANUAL n8n Setup (Do Once — in Browser)

n8n is running at `http://localhost:5678`

### Step 1: First-time Setup
- Open http://localhost:5678
- Create owner account (email + password)

### Step 2: Import Workflows
Import these JSON files one by one (Workflows > Import from File):

1. `n8n/workflows/2.1.1_health_check.json` — health check every 5 min
2. `n8n/workflows/2.3.1_full_pipeline_webhook.json` — main pipeline (bronze > QC > staging > QC > marts > QC > success)
3. `n8n/workflows/2.6.1_success_notification.json` — Slack success message
4. `n8n/workflows/2.6.2_failure_alert.json` — Slack failure @channel alert
5. `n8n/workflows/2.6.3_quality_digest.json` — daily 18:00 quality digest
6. `n8n/workflows/2.6.4_global_error_handler.json` — global error handler

### Step 3: Wire Notifications into Pipeline
After importing, edit `2.3.1_full_pipeline_webhook.json` workflow in n8n UI:
- **Success path** (after "Set Status Success" node) → add **Execute Sub-Workflow** node → select `2.6.1_success_notification`
- **Each failure path** (3 quality failure + 1 general failure nodes) → add **Execute Sub-Workflow** node → select `2.6.2_failure_alert`

This can't be done in JSON because sub-workflow IDs are generated at import time.

### Step 4: Set Global Error Handler
- n8n Settings (gear icon) → Error Workflow → select `2.6.4_global_error_handler`

### Step 5: Activate All Workflows
Toggle each workflow to **Active** (green).

### Step 6: Environment Variables in n8n
These are already in `.env` and passed via docker-compose:
- `PIPELINE_WEBHOOK_SECRET` — webhook auth token
- `SLACK_WEBHOOK_URL` — set this to your actual Slack webhook URL when ready

---

## Frontend Build Fix [FIXED]

**Root cause**: `package-lock.json` was missing. `npm ci` requires it for reproducible builds.

**Fix applied**:
- Generated `package-lock.json` via `npm install --package-lock-only`
- Fixed Dockerfile: removed wildcard from `COPY package.json package-lock.json* ./` → `COPY package.json package-lock.json ./`

---

## Completed Phases (Latest)

### Phase 2.4: File Watcher [DONE]
- watchdog-based directory monitor with debounce logic (10s default)
- DataFileHandler: detects new CSV/Excel files, debounces events
- FileWatcherService: triggers pipeline via API on file detection
- CLI: `python -m datapulse.watcher --debounce 10`
- Docker service: `datapulse-watcher` container
- Tests: test_watcher.py

### Phase 2.8: AI-Light [DONE]
- OpenRouter client with chat + JSON parsing
- AILightService: summaries, anomaly detection (statistical + AI), change narratives
- 4 API endpoints: /status, /summary, /anomalies, /changes
- Frontend: /insights page with AI summary card + anomaly list
- 3 SWR hooks + TypeScript types
- n8n workflow: 2.8.1_ai_insights_digest.json (daily 09:00 → Slack)
- Tests: test_ai_light.py
- Config: `OPENROUTER_API_KEY` + `OPENROUTER_MODEL` in .env

## Remaining Phases

### Phase 4: Public Website / Landing Page
- Marketing/landing page for DataPulse

---

## Docker Commands Reference

```bash
# Start everything (from WSL/Ubuntu)
cd /mnt/c/Users/user/Documents/GitHub/SAAS
docker compose up -d

# Start specific services
docker compose up -d n8n redis
docker compose up -d frontend --build

# Check status
docker compose ps

# View logs
docker compose logs n8n --tail 50
docker compose logs frontend --tail 50

# Run migrations (inside app container)
docker exec -it datapulse-app python -m datapulse.bronze.loader --help

# Run tests
docker exec -it datapulse-api pytest tests/ -v
```

---

## .env Required Variables

```
POSTGRES_USER=datapulse
POSTGRES_PASSWORD=datapulse_dev
POSTGRES_DB=datapulse
DATABASE_URL=postgresql://datapulse:datapulse_dev@localhost:5432/datapulse
REDIS_PASSWORD=datapulse_redis_dev
N8N_ENCRYPTION_KEY=datapulse-n8n-dev-key-change-in-prod
PIPELINE_WEBHOOK_SECRET=datapulse-webhook-dev-secret
SLACK_WEBHOOK_URL=
```

---

## Key URLs (when Docker is running)

| Service | URL |
|---------|-----|
| n8n GUI | http://localhost:5678 |
| FastAPI docs | http://localhost:8000/docs |
| Frontend | http://localhost:3000 |
| pgAdmin | http://localhost:5050 |
| JupyterLab | http://localhost:8888 |
