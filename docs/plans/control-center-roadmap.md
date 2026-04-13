# Control Center — Full Implementation Roadmap

> **Active PR:** `claude/kind-torvalds` → **PR #349**
> **Last updated:** 2026-04-13
> **Branch with code:** `claude/kind-torvalds`

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

## Phase 1-FE — Frontend Remaining Work

**Missing components** (pages and hooks already exist):

| File | What it does |
|------|-------------|
| `frontend/src/components/control-center/profile-form.tsx` | Create/edit pipeline profile form |
| `frontend/src/components/control-center/mapping-editor.tsx` | Two-column table: source col (read-only) + canonical field dropdown |
| `frontend/src/components/control-center/validation-report.tsx` | Renders `ValidationReport` errors/warnings |
| `frontend/src/components/control-center/release-diff.tsx` | Diff between `snapshot_json` of two releases |

**Already exists:**
- `frontend/src/app/(app)/control-center/` — layout, page, sources, profiles, mappings, releases, sync-runs
- `frontend/src/hooks/` — use-connections, use-drafts, use-mappings, use-profiles, use-releases
- `frontend/src/components/control-center/` — connection-form, preview-table

### Fresh-session prompt for Phase 1-FE

```
You are continuing Phase 1-FE of the DataPulse Control Center (branch: claude/kind-torvalds, PR #349).

Backend is 100% done. Four frontend components are missing.
Pages and SWR hooks already exist — you are only building the components.

Create these four files following the patterns in connection-form.tsx and preview-table.tsx:

1. frontend/src/components/control-center/profile-form.tsx
   - Form fields: display_name (text), target_domain (select from /canonical-domains),
     is_default (checkbox), quality_thresholds (JSON textarea, optional)
   - Uses useCanonicalDomains hook (already exists)
   - Calls POST /profiles or PATCH /profiles/{id} via fetchAPI

2. frontend/src/components/control-center/mapping-editor.tsx
   - Two-column <table>: left = source column name (read-only, from preview result),
     right = canonical field dropdown (from /canonical-domains schema fields)
   - Props: columns (PreviewColumn[]), canonicalFields (string[]), onChange (callback)
   - No external libraries — plain HTML table + <select> elements

3. frontend/src/components/control-center/validation-report.tsx
   - Renders a ValidationReport: ok boolean, errors[], warnings[]
   - Errors in red, warnings in amber, green checkmark if ok=true and no errors
   - Each item shows: code, message, field (optional)

4. frontend/src/components/control-center/release-diff.tsx
   - Takes two snapshot_json objects (current release, prior release)
   - Shows added/removed/changed keys in a styled diff view
   - Use plain string comparison — no diff library needed

Reference files to read first:
  frontend/src/components/control-center/connection-form.tsx
  frontend/src/components/control-center/preview-table.tsx
  frontend/src/hooks/use-connections.ts
  frontend/src/hooks/use-profiles.ts

Run: cd frontend && npx tsc --noEmit
```

---

## Phase 2 — Google Sheets Connector + Scheduled Sync

### Goal
Allow tenants to register a Google Sheet as a source connection and have it auto-synced on a cron schedule.

### New files to create

| File | Purpose |
|------|---------|
| `migrations/047_control_center_schedules.sql` | `sync_schedules` table |
| `src/datapulse/control_center/connectors/google_sheets.py` | `GoogleSheetsConnector` |
| `ScheduledSyncRepository` in `repository.py` | `create_schedule`, `list_schedules`, `delete_schedule` |
| Schedule service methods in `service.py` | Thin wrappers over repo |
| 2 endpoints in `routes/control_center.py` | `POST/DELETE /connections/{id}/schedule` |
| Frontend schedule toggle on sources page | Cron input + human-readable preview |

### Migration 047

```sql
-- migrations/047_control_center_schedules.sql
CREATE TABLE IF NOT EXISTS public.sync_schedules (
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

CREATE INDEX IF NOT EXISTS idx_sync_schedules_active
    ON public.sync_schedules (is_active, connection_id);

ALTER TABLE public.sync_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sync_schedules FORCE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON public.sync_schedules
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON public.sync_schedules
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
```

### GoogleSheetsConnector sketch

```python
# src/datapulse/control_center/connectors/google_sheets.py
# config_json fields: sheet_id, range (e.g. "Sheet1!A:Z"), max_rows
# credentials_ref points to source_credentials row (Phase 3 provides proper creds;
#   Phase 2 may use config_json.service_account_key as a temporary workaround)
# Uses: google-api-python-client, google-auth
# Must implement SourceConnector protocol (base.py)
```

### APScheduler wiring

Read `src/datapulse/scheduler.py` for the existing APScheduler setup pattern.
On app startup, load all `is_active=True` rows from `sync_schedules` and register
each as an APScheduler `CronTrigger` job calling `service.trigger_sync(connection_id, tenant_id)`.

### New permissions (append to migration 046)

```sql
INSERT INTO public.role_permissions (role, permission) VALUES
  ('owner', 'control_center:sync:schedule'),
  ('admin', 'control_center:sync:schedule')
ON CONFLICT DO NOTHING;
```

### Fresh-session prompt for Phase 2

```
You are implementing Phase 2 of the DataPulse Control Center (branch: claude/kind-torvalds, PR #349).
Phase 1 (1a–1e + 1-FE) is complete. Backend and frontend Phase 1 are done.

Phase 2 goal: Google Sheets connector + scheduled sync.

Read these files first (in parallel):
  src/datapulse/scheduler.py                               — APScheduler setup pattern
  src/datapulse/control_center/connectors/file_upload.py   — connector pattern to follow
  src/datapulse/control_center/connectors/base.py          — SourceConnector protocol
  src/datapulse/control_center/repository.py               — existing repo pattern
  src/datapulse/control_center/service.py                  — existing service pattern
  migrations/046_control_center_permissions.sql            — permission insert pattern

Then implement in this order:
1. migrations/047_control_center_schedules.sql
2. src/datapulse/control_center/connectors/google_sheets.py  — GoogleSheetsConnector
3. ScheduledSyncRepository in repository.py  — create_schedule, list_schedules, delete_schedule
4. Service methods in service.py  — create_schedule, delete_schedule, list_schedules
5. Two endpoints in routes/control_center.py:
     POST   /connections/{id}/schedule    (requires control_center:sync:schedule)
     DELETE /connections/{id}/schedule    (requires control_center:sync:schedule)
6. Register schedules with APScheduler on app startup in scheduler.py
7. Frontend: "Schedule" toggle + cron input on sources page
8. Tests: tests/test_control_center_schedules.py

Architecture constraints (non-negotiable):
  - tenant_id is INT (never UUID)
  - Route → Service → Repository (never skip layers)
  - require_permission("control_center:sync:schedule") on schedule endpoints
  - FEATURE_CONTROL_CENTER check before every new endpoint

Run CI locally before pushing:
  ruff format --check src/ tests/
  ruff check src/ tests/
  mypy src/datapulse/control_center/ --ignore-missing-imports
  pytest tests/test_control_center_schedules.py -x -q
```

---

## Phase 3 — Postgres/SQL Server Connectors + pgcrypto Credentials

### Goal
Support direct database connections as sources. Credentials must be encrypted at rest
using pgcrypto — **never stored in `config_json`**.

### New files to create

| File | Purpose |
|------|---------|
| `migrations/048_control_center_credentials.sql` | `source_credentials` table (pgcrypto) |
| `src/datapulse/control_center/credentials.py` | `store_credential`, `load_credential` |
| `src/datapulse/control_center/connectors/postgres.py` | `PostgresConnector` |
| `src/datapulse/control_center/connectors/mssql.py` | `MSSQLConnector` (Phase 3b, optional) |

### Migration 048

```sql
-- migrations/048_control_center_credentials.sql
-- pgcrypto extension already enabled in existing migrations
CREATE TABLE IF NOT EXISTS public.source_credentials (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id        INT NOT NULL REFERENCES bronze.tenants(tenant_id),
    connection_id    INT NOT NULL REFERENCES public.source_connections(id),
    credential_type  VARCHAR(50) NOT NULL,  -- 'password' | 'service_account' | 'connection_string'
    encrypted_value  TEXT NOT NULL,         -- pgp_sym_encrypt(plain, key)
    created_by       TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_source_credentials_conn UNIQUE (connection_id, credential_type)
);
-- Encryption key from env: CONTROL_CENTER_CREDS_KEY
-- NEVER return encrypted_value in any API response
```

### credentials.py contract

```python
# src/datapulse/control_center/credentials.py
def store_credential(
    session, *, connection_id: int, tenant_id: int,
    cred_type: str, plain_value: str
) -> int:
    """Encrypt with pgp_sym_encrypt and persist. Returns row id."""

def load_credential(
    session, *, connection_id: int, tenant_id: int
) -> str | None:
    """Decrypt with pgp_sym_decrypt and return plaintext, or None."""
    # Key from settings.control_center_creds_key
    # NEVER log the return value
```

### PostgresConnector sketch

```python
# config_json fields: host, port, database, schema_name, table_name, username
# credentials_ref = str(credential_row_id) — set after store_credential()
# test(): psycopg2 connect with connect_timeout=5, run SELECT 1
# preview(): SELECT * FROM {schema}.{table} LIMIT {max_rows}
```

### Config addition

```python
# src/datapulse/core/config.py — append to Settings:
control_center_creds_key: str = ""
```

### Security rules (non-negotiable)

- `encrypted_value` never appears in any Pydantic response model field
- Credential values never logged — not even truncated
- `credentials_ref` on `source_connections` = only the row **id** as a string, never the secret
- Rotation: re-encrypt all rows when `CONTROL_CENTER_CREDS_KEY` changes (write a helper script)
- Frontend: `<input type="password">`, value never echoed back by `GET /connections/{id}`

### Fresh-session prompt for Phase 3

```
You are implementing Phase 3 of the DataPulse Control Center (branch: claude/kind-torvalds, PR #349).
Phases 1a–1e, 1-FE, and Phase 2 are complete.

Phase 3 goal: pgcrypto credential storage + Postgres connector.

Read these files first (in parallel):
  src/datapulse/control_center/connectors/base.py           — SourceConnector protocol
  src/datapulse/control_center/connectors/file_upload.py    — connector pattern
  src/datapulse/core/config.py                              — Settings class
  src/datapulse/control_center/models.py                    — SourceConnection model
  migrations/047_control_center_schedules.sql               — migration pattern to follow

Then implement in this order:
1. migrations/048_control_center_credentials.sql
2. src/datapulse/control_center/credentials.py  — store_credential + load_credential
3. Add control_center_creds_key: str = "" to src/datapulse/core/config.py
4. src/datapulse/control_center/connectors/postgres.py  — PostgresConnector
5. Wire credentials into connection CRUD in service.py:
   - store_credential() on POST/PATCH when password fields present
   - load_credential() inside test_connection() and preview_connection()
6. Frontend: credential fields in connection-form.tsx (type="password", never echoed)
7. Tests: tests/test_control_center_credentials.py

Security rules (MUST follow — CI will fail otherwise):
  - encrypted_value never in any Pydantic response model
  - credentials never logged
  - credentials_ref = str(row_id) only
  - GET /connections/{id} never returns password

Run CI locally before pushing:
  ruff format --check src/ tests/
  ruff check src/ tests/
  mypy src/datapulse/control_center/ --ignore-missing-imports
  pytest tests/test_control_center_credentials.py -x -q
```

---

## Phase 4 — Onboarding Integration + Customer Self-Service

### Goal
Close the onboarding loop: first publish triggers `configure_first_profile` step.
Add a health-summary endpoint powering a dashboard card.

### Changes required

| File | Change |
|------|--------|
| `src/datapulse/onboarding/models.py` | Append `"configure_first_profile"` to `ONBOARDING_STEPS` |
| `src/datapulse/control_center/service.py` | Call `onboarding_svc.complete_step()` at end of `publish_draft()` for tenant's first release |
| `src/datapulse/api/routes/control_center.py` | Add `GET /control-center/health-summary` |
| `frontend/src/app/(app)/control-center/page.tsx` | Add health card (connection count, last sync, active release) |
| Onboarding checklist component | Add "Configure pipeline profile" step with link |

### publish_draft() wiring snippet

```python
# End of publish_draft() — after release row is created:
if self._releases.count_for_tenant(tenant_id) == 1:
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
        pass  # step already completed or not yet in workflow
```

### Health summary response shape

```
GET /api/v1/control-center/health-summary
{
  "connection_count": int,
  "active_connections": int,
  "last_sync_at": "ISO datetime | null",
  "active_release_version": "int | null",
  "pending_drafts": int
}
No new DB tables — all data from existing queries.
```

### Fresh-session prompt for Phase 4

```
You are implementing Phase 4 of the DataPulse Control Center (branch: claude/kind-torvalds, PR #349).
Phases 1a–1e, 1-FE, 2, and 3 are complete.

Phase 4 goal: onboarding integration + health-summary endpoint + dashboard card.

Read these files first (in parallel):
  src/datapulse/onboarding/models.py            — ONBOARDING_STEPS list
  src/datapulse/onboarding/service.py           — complete_step() signature
  src/datapulse/onboarding/repository.py        — OnboardingRepository
  src/datapulse/control_center/service.py       — publish_draft() implementation
  src/datapulse/api/routes/control_center.py    — existing route patterns
  frontend/src/app/(app)/control-center/page.tsx  — current default page

Then implement in this order:
1. Append "configure_first_profile" to ONBOARDING_STEPS in onboarding/models.py
2. Wire onboarding_svc.complete_step() at end of publish_draft() in service.py
   (guard: only when release count for tenant == 1)
3. Add GET /control-center/health-summary endpoint in routes/control_center.py
4. Add health card to control-center default page
5. Add "Configure pipeline profile" step to onboarding checklist (link to /control-center/profiles)
6. Tests: tests/test_control_center_phase4.py
   - first publish → onboarding step completed
   - second publish → ValueError caught silently, no double-complete
   - health-summary → correct aggregated counts

Run CI locally before pushing:
  ruff format --check src/ tests/
  ruff check src/ tests/
  pytest tests/test_control_center_phase4.py -x -q
```

---

## Architecture Constraints (enforced across all phases)

1. `preview.py` — never imports from `bronze.*`
2. `pipeline_releases` — append-only, no UPDATE/DELETE ever
3. `tenant_id` — always `INT`, never UUID
4. Credentials — never in `config_json`, never in logs, never in API responses
5. `require_permission("control_center:*")` on every endpoint
6. `FEATURE_CONTROL_CENTER=false` by default; check before every new endpoint
7. Route → Service → Repository — no skipping layers
8. Primary keys: `BIGINT GENERATED ALWAYS AS IDENTITY` (not UUID)
9. Every migration is idempotent (`IF NOT EXISTS`, `DO $$ BEGIN...EXCEPTION`)

---

## Key File Locations

| What | Where |
|------|-------|
| All Control Center Python | `src/datapulse/control_center/` |
| API routes | `src/datapulse/api/routes/control_center.py` |
| Migrations (done) | `migrations/041_*` – `046_*` |
| Migrations (pending) | `migrations/047_*` (Phase 2), `048_*` (Phase 3) |
| Frontend pages | `frontend/src/app/(app)/control-center/` |
| Frontend hooks | `frontend/src/hooks/use-{connections,profiles,mappings,drafts,releases}.ts` |
| Frontend components | `frontend/src/components/control-center/` |
| Tests | `tests/test_control_center_*.py` |
| Feature flag (backend) | `src/datapulse/core/config.py` → `feature_control_center` |
| Feature flag (frontend) | `NEXT_PUBLIC_FEATURE_CONTROL_CENTER` in `.env` |

---

## CI Commands (run before every push)

```bash
ruff format --check src/ tests/
ruff check src/ tests/
mypy src/datapulse/control_center/ --ignore-missing-imports
pytest tests/test_control_center_*.py -x -q --tb=short
cd frontend && npx tsc --noEmit
```
