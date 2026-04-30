# Control Center — Implementation Roadmap

> **Branch:** `claude/kind-torvalds` → **PR #349**
> **Last updated:** 2026-04-13

---

## Status Overview

| Phase | Scope | Status |
|-------|-------|--------|
| 1a | Schema · canonical registry · RBAC · READ API · sidebar nav | ✅ Done |
| 1b | Connection CRUD · file_upload connector · preview engine | ✅ Done |
| 1c | Profile CRUD · Mapping CRUD · validation engine | ✅ Done |
| 1d | Draft → Validate → Preview → Publish · Rollback | ✅ Done |
| 1e | Sync trigger · sync history | ✅ Done |
| 1-FE | Frontend pages · hooks · components | 🔶 80% done — 4 components missing |
| 2 | Google Sheets connector · scheduled sync | ⬜ Pending |
| 3 | Postgres/SQL Server connectors · pgcrypto credentials | ⬜ Pending |
| 4 | Onboarding integration · customer self-service | ⬜ Pending |

---

## Phase 1 — Frontend Remaining Work

**Missing components** (pages and hooks already exist):
- `frontend/src/components/control-center/profile-form.tsx`
- `frontend/src/components/control-center/mapping-editor.tsx` — two-column table: source col (read-only) + canonical field dropdown
- `frontend/src/components/control-center/validation-report.tsx` — renders `ValidationReport` errors/warnings
- `frontend/src/components/control-center/release-diff.tsx` — diff between snapshot_json of two releases

**Existing:**
- `frontend/src/app/(app)/control-center/` — layout, page, sources, profiles, mappings, releases, sync-runs
- `frontend/src/hooks/` — use-connections, use-drafts, use-mappings, use-profiles, use-releases
- `frontend/src/components/control-center/` — connection-form, preview-table

---

## Phase 2 — Google Sheets Connector + Scheduled Sync

### Goal
Allow tenants to register a Google Sheet as a source connection and have it auto-synced on a schedule.

### Backend tasks
- `src/datapulse/control_center/connectors/google_sheets.py` — implements `SourceConnector`
  - `test()`: validates OAuth token + sheet ID is accessible
  - `preview()`: reads first N rows via Google Sheets API
  - Uses service account JSON (stored via Phase 3 credentials system, or Phase 2 can use `config_json.service_account_key` as a temporary workaround)
- `migrations/047_control_center_schedules.sql` — `sync_schedules` table
  ```sql
  CREATE TABLE public.sync_schedules (
      id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
      tenant_id     INT NOT NULL REFERENCES bronze.tenants(tenant_id),
      connection_id INT NOT NULL REFERENCES public.source_connections(id),
      cron_expr     VARCHAR(100) NOT NULL,  -- e.g. '0 6 * * *'
      is_active     BOOL NOT NULL DEFAULT true,
      last_run_at   TIMESTAMPTZ,
      created_by    TEXT,
      created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
  );
  ```
- `ScheduledSyncRepository` + service methods: `create_schedule`, `list_schedules`, `delete_schedule`
- Register schedules with APScheduler on app startup (see `src/datapulse/scheduler.py` pattern)
- New endpoints: `POST /connections/{id}/schedule`, `DELETE /connections/{id}/schedule`
- Google Sheets read: use `google-api-python-client` + `google-auth`

### Frontend tasks
- Add "Schedule" toggle to sources page
- Cron expression input field (with human-readable preview)

### Key files to read first
- `src/datapulse/scheduler.py` — APScheduler setup pattern
- `src/datapulse/control_center/connectors/file_upload.py` — connector pattern to follow
- `migrations/046_control_center_permissions.sql` — add `control_center:sync:schedule` permission

---

## Phase 3 — Postgres/SQL Server Connectors + pgcrypto Credentials

### Goal
Support direct database connections as sources. Credentials (password/DSN) must be encrypted at rest — never in `config_json`.

### Backend tasks

**Migration 048 — source_credentials:**
```sql
CREATE TABLE public.source_credentials (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id     INT NOT NULL REFERENCES bronze.tenants(tenant_id),
    connection_id INT NOT NULL REFERENCES public.source_connections(id),
    credential_type VARCHAR(50) NOT NULL,  -- 'password', 'service_account', 'connection_string'
    encrypted_value TEXT NOT NULL,         -- pgp_sym_encrypt(value, key)
    created_by    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Encryption key comes from env var CONTROL_CENTER_CREDS_KEY
```

**Credential service** (`src/datapulse/control_center/credentials.py`):
```python
def store_credential(session, *, connection_id, tenant_id, cred_type, plain_value) -> int
def load_credential(session, *, connection_id, tenant_id) -> str | None
```
- Uses `pgp_sym_encrypt` / `pgp_sym_decrypt` via raw SQL
- Key sourced from `settings.control_center_creds_key` (never hardcoded)
- `credentials_ref` on `source_connections` stores the credential row ID as a string reference

**Connectors:**
- `src/datapulse/control_center/connectors/postgres.py` — `PostgresConnector`
  - `test()`: attempts `SELECT 1` via psycopg2 with a 5s timeout
  - `preview()`: `SELECT * FROM {schema}.{table} LIMIT {max_rows}`
- `src/datapulse/control_center/connectors/mssql.py` — `MSSQLConnector` (optional, Phase 3b)

**Config:**
- Add `control_center_creds_key: str = ""` to `src/datapulse/core/config.py`

### Frontend tasks
- Add credential fields to connection form (password field, never echoed back)
- Visual indicator when credentials are stored vs missing

### Security rules (non-negotiable)
- Never return `encrypted_value` in any API response
- Never log credential values
- `credentials_ref` in `source_connections` never contains the actual secret
- Rotate `CONTROL_CENTER_CREDS_KEY` = re-encrypt all rows (write a migration helper)

---

## Phase 4 — Onboarding Integration + Customer Self-Service

### Goal
Complete the loop: publishing the first pipeline profile marks onboarding step `configure_first_profile` as done, driving the tenant through the DataPulse setup wizard.

### Backend tasks

**Onboarding step** (one-line change):
- `src/datapulse/onboarding/models.py` → append `"configure_first_profile"` to `ONBOARDING_STEPS`

**Service wiring** (in `publish_draft`, after release is created):
```python
# At the end of publish_draft(), if this is the tenant's first release:
from datapulse.onboarding.service import OnboardingService
from datapulse.onboarding.repository import OnboardingRepository
onboarding_svc = OnboardingService(OnboardingRepository(self._session))
try:
    onboarding_svc.complete_step(
        tenant_id=tenant_id,
        user_id=published_by or "system",
        step="configure_first_profile",
    )
except ValueError:
    pass  # step already completed or not in workflow yet
```

**Customer self-service dashboard** (new endpoint):
- `GET /control-center/health-summary` — returns connection count, last sync, active releases, pending drafts
- No new tables needed — all data from existing queries

### Frontend tasks
- Onboarding checklist shows "Configure pipeline profile" step with link to `/control-center/profiles`
- Dashboard home shows Control Center health card (last sync, active connections, release version)

---

## Architecture Constraints (always enforced)

1. `preview.py` — never imports from `bronze.*`
2. `releases` — append-only, no UPDATE/DELETE ever
3. `tenant_id` — always `INT`, never UUID
4. Credentials — never in `config_json`, never in logs, never in API responses
5. `require_permission("control_center:*")` on every endpoint
6. `FEATURE_CONTROL_CENTER=false` by default in all environments
7. Route → Service → Repository — no skipping layers

---

## Key File Locations

| What | Where |
|------|-------|
| All Control Center Python | `src/datapulse/control_center/` |
| API routes | `src/datapulse/api/routes/control_center.py` |
| Migrations | `migrations/041_*` through `migrations/046_*` |
| Frontend pages | `frontend/src/app/(app)/control-center/` |
| Frontend hooks | `frontend/src/hooks/use-{connections,profiles,mappings,drafts,releases}.ts` |
| Frontend components | `frontend/src/components/control-center/` |
| Tests | `tests/test_control_center_*.py` |
| Feature flag (backend) | `src/datapulse/core/config.py` → `feature_control_center` |
| Feature flag (frontend) | `NEXT_PUBLIC_FEATURE_CONTROL_CENTER` in `.env` |
| Original full plan | `.claude/plans/swirling-marinating-nebula.md` |
