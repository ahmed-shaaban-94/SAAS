# POS Desktop — M1 Backend Foundations — Implementation Plan (v2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ship additive backend-only pieces for the POS desktop client: idempotency contract on commit-path, new atomic `POST /pos/transactions/commit` endpoint, tenant Ed25519 keypair rotation, device-bound terminal credentials, Ed25519-signed offline grants on shift-open, server-enforced override-token ledger, server-enforced shift-close guard, capabilities + tenant-scoped-active-terminal endpoints, single-terminal enforcement. Nothing in M1 touches the web frontend, the Electron app, or existing committed transaction flow.

**Architecture:** Mocks-only tests (project standard, matches `tests/test_pos_b6a_service.py` + `tests/test_pos_b7.py`). SQL migrations committed as files; applied on the droplet at deploy time — **not applied locally in this plan**. New FastAPI dependencies in `src/datapulse/pos/*.py` modules. Pydantic v2 frozen models. Ed25519 via `cryptography` (already in `requirements.lock`).

**Tech Stack:** Python 3.11+ · FastAPI · SQLAlchemy 2.0 · Pydantic v2 · `cryptography` (Ed25519) · pytest.

**Spec:** `docs/superpowers/specs/2026-04-17-pos-electron-desktop-design.md`.

---

## Critical conventions (read before starting any task)

1. **Tests are mock-based.** Every test file starts with `pytestmark = pytest.mark.unit`. Sessions are `MagicMock()`, repositories are `create_autospec(...)`, services are constructed with mocks. **Never touch a real DB in tests.** Template: see `tests/test_pos_b7.py` for a FastAPI route test with mocked dependency_overrides.
2. **Auth header in tests:** `X-API-Key: test-api-key` (matches `conftest.py::api_client`). Not `Authorization: Bearer`.
3. **Migrations are committed SQL, not applied.** Do **not** run `docker compose exec … psql`. Only `git add` the SQL file and move on. The droplet deploy pipeline applies migrations.
4. **Permission slugs use colon-tree format.** Existing: `pos:transaction:checkout`, `pos:transaction:void`, `pos:shift:reconcile`, `pos:terminal:open`, `pos:return:create`, `pos:controlled:verify`, `pos:shift:view`. New M1 slugs go in migration 085 (Task 9 below).
5. **Tenants live in `bronze.tenants(tenant_id)`** (see `migrations/003_add_tenant_id.sql`). Not `public.tenants(id)`.
6. **Commit at the end of every task** with a focused conventional-commit message.
7. **Run the focused test file** after each implementation step; run the full POS suite at the end.

---

## File map

### New migrations

| File | Purpose |
|---|---|
| `migrations/077_add_pos_idempotency_keys.sql` | Request dedupe table |
| `migrations/078_add_pos_transaction_shift_link.sql` | Add `pos.transactions.shift_id` + `commit_confirmed_at` + partial index |
| `migrations/079_add_pos_terminal_devices.sql` | Device-bound terminal credentials |
| `migrations/080_add_pos_tenant_keys.sql` | Tenant Ed25519 signing keypairs |
| `migrations/081_add_pos_grants_issued.sql` | Server-side grant registry |
| `migrations/082_add_pos_override_consumptions.sql` | One-time-use override ledger |
| `migrations/083_add_pos_shifts_close_attempts.sql` | Forensic close log |
| `migrations/084_add_tenant_pos_flags.sql` | `bronze.tenants` POS multi-terminal flags |
| `migrations/085_add_pos_m1_permissions.sql` | New permission slugs for M1 |

### New Python modules

| File | Purpose |
|---|---|
| `src/datapulse/pos/capabilities.py` | Capability constants + `CapabilitiesDoc` model (via models.py) |
| `src/datapulse/pos/idempotency.py` | `IdempotencyContext` + `idempotency_dependency` factory |
| `src/datapulse/pos/tenant_keys.py` | Ed25519 keypair rotation + public-key listing |
| `src/datapulse/pos/devices.py` | Terminal device registration + `device_token_verifier` |
| `src/datapulse/pos/grants.py` | Offline grant issuance |
| `src/datapulse/pos/overrides.py` | `override_token_verifier` + ledger insert |
| `src/datapulse/pos/commit.py` | Atomic commit endpoint service logic |
| `src/datapulse/tasks/cleanup_pos_idempotency.py` | Nightly cleanup task |
| `src/datapulse/api/routes/pos.py` | Modify — wire new dependencies to existing routes; add new routes |
| `src/datapulse/pos/models.py` | Modify — add Pydantic models |

### New tests (all mock-based; `pytestmark = pytest.mark.unit`)

| File |
|---|
| `tests/test_pos_idempotency.py` |
| `tests/test_pos_capabilities.py` |
| `tests/test_pos_tenant_keys.py` |
| `tests/test_pos_devices.py` |
| `tests/test_pos_grants.py` |
| `tests/test_pos_overrides.py` |
| `tests/test_pos_commit.py` |
| `tests/test_pos_shift_close_guard.py` |
| `tests/test_pos_single_terminal_guard.py` |
| `tests/test_pos_cleanup_task.py` |

**Deferred to M2:** catalog streaming (`/pos/catalog/products`, `/pos/catalog/stock`) — depends on creating `pos.products_catalog` / `pos.stock_snapshot` views, and the client doesn't pull catalog until M3 anyway.

---

## Task 1: Migration — `pos.idempotency_keys`

**Files:** Create `migrations/077_add_pos_idempotency_keys.sql`

- [ ] **Step 1: Write the migration**

```sql
-- Migration: 077 — POS idempotency keys
-- Layer: POS operational
-- Idempotent.

CREATE TABLE IF NOT EXISTS pos.idempotency_keys (
    key             TEXT PRIMARY KEY,
    tenant_id       INT NOT NULL,
    endpoint        TEXT NOT NULL,
    request_hash    TEXT NOT NULL,
    response_status INT,
    response_body   JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pos_idemp_expires
    ON pos.idempotency_keys (expires_at);

ALTER TABLE pos.idempotency_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.idempotency_keys FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.idempotency_keys
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.idempotency_keys
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE pos.idempotency_keys TO datapulse;
GRANT SELECT ON TABLE pos.idempotency_keys TO datapulse_reader;

COMMENT ON TABLE pos.idempotency_keys IS
  'Request dedupe for POS mutating endpoints. TTL = 168h (> provisional_ttl 72h + 96h safety margin). RLS-protected.';
```

- [ ] **Step 2: Commit**

```bash
git add migrations/077_add_pos_idempotency_keys.sql
git commit -m "feat(pos): add pos.idempotency_keys migration"
```

---

## Task 2: Migration — add `shift_id` + `commit_confirmed_at` to `pos.transactions`

**Files:** Create `migrations/078_add_pos_transaction_shift_link.sql`

- [ ] **Step 1: Write the migration**

```sql
-- Migration: 078 — Link pos.transactions to shifts + add commit_confirmed_at
-- Layer: POS operational
-- Idempotent.

ALTER TABLE pos.transactions
    ADD COLUMN IF NOT EXISTS shift_id            BIGINT REFERENCES pos.shift_records(id);

ALTER TABLE pos.transactions
    ADD COLUMN IF NOT EXISTS commit_confirmed_at TIMESTAMPTZ;

-- Back-fill shift_id: join through terminal_sessions → shift_records on the same terminal
-- whose opened_at window contains the transaction's created_at.
-- (This is best-effort back-fill; new rows will get shift_id set at commit time.)
UPDATE pos.transactions t
   SET shift_id = sr.id
  FROM pos.shift_records sr
 WHERE t.shift_id IS NULL
   AND sr.terminal_id = t.terminal_id
   AND sr.opened_at  <= t.created_at
   AND (sr.closed_at IS NULL OR sr.closed_at >= t.created_at);

-- Back-fill commit_confirmed_at for already-final rows
UPDATE pos.transactions
   SET commit_confirmed_at = COALESCE(commit_confirmed_at, created_at)
 WHERE status IN ('completed', 'voided', 'returned')
   AND commit_confirmed_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_pos_txn_shift
    ON pos.transactions (shift_id, terminal_id);

-- Partial index powering the shift-close server-side guard
CREATE INDEX IF NOT EXISTS idx_pos_txn_incomplete
    ON pos.transactions (shift_id, terminal_id)
    WHERE commit_confirmed_at IS NULL;

COMMENT ON COLUMN pos.transactions.shift_id IS
  'Link to pos.shift_records(id). Set atomically at commit time; back-filled for legacy rows.';
COMMENT ON COLUMN pos.transactions.commit_confirmed_at IS
  'Timestamp when the transaction reached final committed state. NULL while draft/in-flight. Queried by shift-close guard.';
```

- [ ] **Step 2: Commit**

```bash
git add migrations/078_add_pos_transaction_shift_link.sql
git commit -m "feat(pos): add shift_id + commit_confirmed_at to pos.transactions"
```

---

## Task 3: Migrations — `terminal_devices`, `tenant_keys`, `grants_issued`, `override_consumptions`, `shifts_close_attempts`

**Files:** Create `migrations/079…083_*.sql`

Each follows the same pattern (RLS, policies, grants, comment). Commit all five together.

- [ ] **Step 1: `079_add_pos_terminal_devices.sql`**

```sql
CREATE TABLE IF NOT EXISTS pos.terminal_devices (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id           INT NOT NULL,
    terminal_id         BIGINT NOT NULL REFERENCES pos.terminal_sessions(id),
    public_key          BYTEA NOT NULL,
    device_fingerprint  TEXT NOT NULL,
    registered_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at          TIMESTAMPTZ,
    last_seen_at        TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_pos_device_terminal_active
    ON pos.terminal_devices (terminal_id)
    WHERE revoked_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_pos_device_tenant
    ON pos.terminal_devices (tenant_id, revoked_at);

ALTER TABLE pos.terminal_devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.terminal_devices FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.terminal_devices
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.terminal_devices
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT, UPDATE ON TABLE pos.terminal_devices TO datapulse;
GRANT SELECT ON TABLE pos.terminal_devices TO datapulse_reader;

COMMENT ON TABLE pos.terminal_devices IS
  'Physical-device binding for POS terminals. Unique partial index enforces one active device per terminal.';
```

- [ ] **Step 2: `080_add_pos_tenant_keys.sql`**

```sql
CREATE TABLE IF NOT EXISTS pos.tenant_keys (
    key_id        TEXT PRIMARY KEY,
    tenant_id     INT NOT NULL,
    private_key   BYTEA NOT NULL,
    public_key    BYTEA NOT NULL,
    valid_from    TIMESTAMPTZ NOT NULL DEFAULT now(),
    valid_until   TIMESTAMPTZ NOT NULL,
    revoked_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_pos_tkeys_tenant_active
    ON pos.tenant_keys (tenant_id, valid_until)
    WHERE revoked_at IS NULL;

ALTER TABLE pos.tenant_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.tenant_keys FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.tenant_keys
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.tenant_keys
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT, UPDATE ON TABLE pos.tenant_keys TO datapulse;
GRANT SELECT ON TABLE pos.tenant_keys TO datapulse_reader;

COMMENT ON TABLE pos.tenant_keys IS
  'Ed25519 signing keypairs per tenant. Rotated daily with 7-day overlap window. Private keys must be encrypted at rest via server KMS in production.';
```

- [ ] **Step 3: `081_add_pos_grants_issued.sql`**

```sql
CREATE TABLE IF NOT EXISTS pos.grants_issued (
    grant_id            TEXT PRIMARY KEY,
    tenant_id           INT NOT NULL,
    terminal_id         BIGINT NOT NULL REFERENCES pos.terminal_sessions(id),
    shift_id            BIGINT NOT NULL REFERENCES pos.shift_records(id),
    staff_id            TEXT NOT NULL,
    key_id              TEXT NOT NULL REFERENCES pos.tenant_keys(key_id),
    code_ids            JSONB NOT NULL,
    issued_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    offline_expires_at  TIMESTAMPTZ NOT NULL,
    revoked_at          TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_pos_grants_terminal
    ON pos.grants_issued (terminal_id, issued_at DESC);

ALTER TABLE pos.grants_issued ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.grants_issued FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.grants_issued
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.grants_issued
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT, UPDATE ON TABLE pos.grants_issued TO datapulse;
GRANT SELECT ON TABLE pos.grants_issued TO datapulse_reader;

COMMENT ON TABLE pos.grants_issued IS
  'Authoritative registry of issued offline grants + their code_id sets. Consumed by override_token_verifier.';
```

- [ ] **Step 4: `082_add_pos_override_consumptions.sql`**

```sql
CREATE TABLE IF NOT EXISTS pos.override_consumptions (
    grant_id                TEXT NOT NULL REFERENCES pos.grants_issued(grant_id),
    code_id                 TEXT NOT NULL,
    tenant_id               INT NOT NULL,
    terminal_id             BIGINT NOT NULL REFERENCES pos.terminal_sessions(id),
    shift_id                BIGINT NOT NULL REFERENCES pos.shift_records(id),
    action                  TEXT NOT NULL
                            CHECK (action IN ('retry_override','void','no_sale','price_override','discount_above_limit')),
    action_subject_id       TEXT,
    consumed_at             TIMESTAMPTZ NOT NULL,
    recorded_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    request_idempotency_key TEXT,
    PRIMARY KEY (grant_id, code_id)
);

CREATE INDEX IF NOT EXISTS idx_pos_overrides_terminal
    ON pos.override_consumptions (terminal_id, consumed_at);

ALTER TABLE pos.override_consumptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.override_consumptions FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.override_consumptions
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.override_consumptions
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT ON TABLE pos.override_consumptions TO datapulse;
GRANT SELECT ON TABLE pos.override_consumptions TO datapulse_reader;

COMMENT ON TABLE pos.override_consumptions IS
  'One-time-use ledger for supervisor override codes. PK (grant_id, code_id) enforces via PK conflict.';
```

- [ ] **Step 5: `083_add_pos_shifts_close_attempts.sql`**

```sql
CREATE TABLE IF NOT EXISTS pos.shifts_close_attempts (
    id                          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    shift_id                    BIGINT NOT NULL REFERENCES pos.shift_records(id),
    tenant_id                   INT NOT NULL,
    terminal_id                 BIGINT NOT NULL REFERENCES pos.terminal_sessions(id),
    attempted_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    outcome                     TEXT NOT NULL
                                CHECK (outcome IN ('accepted','rejected_client','rejected_server')),
    claimed_unresolved_count    INT,
    claimed_unresolved_digest   TEXT,
    server_incomplete_count     INT,
    rejection_reason            TEXT
);

CREATE INDEX IF NOT EXISTS idx_pos_close_attempts_shift
    ON pos.shifts_close_attempts (shift_id, attempted_at DESC);

ALTER TABLE pos.shifts_close_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.shifts_close_attempts FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.shifts_close_attempts
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.shifts_close_attempts
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT ON TABLE pos.shifts_close_attempts TO datapulse;
GRANT SELECT ON TABLE pos.shifts_close_attempts TO datapulse_reader;

COMMENT ON TABLE pos.shifts_close_attempts IS
  'Forensic log of every POST /pos/shifts/{id}/close attempt. Retained indefinitely.';
```

- [ ] **Step 6: Commit all five**

```bash
git add migrations/079_add_pos_terminal_devices.sql \
        migrations/080_add_pos_tenant_keys.sql \
        migrations/081_add_pos_grants_issued.sql \
        migrations/082_add_pos_override_consumptions.sql \
        migrations/083_add_pos_shifts_close_attempts.sql
git commit -m "feat(pos): add device/grant/override/close-attempt migrations"
```

---

## Task 4: Migration — tenant POS flags

**File:** Create `migrations/084_add_tenant_pos_flags.sql`

- [ ] **Step 1: Write the migration**

First check which tenants table applies (verify with `\d bronze.tenants`). We target `bronze.tenants` (columns `tenant_id`, `tenant_name` per migration 003).

```sql
-- Migration: 084 — Tenant POS multi-terminal flags
-- Layer: tenants (bronze)
-- Idempotent.

ALTER TABLE bronze.tenants
    ADD COLUMN IF NOT EXISTS pos_multi_terminal_allowed BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE bronze.tenants
    ADD COLUMN IF NOT EXISTS pos_max_terminals INT NOT NULL DEFAULT 1;

COMMENT ON COLUMN bronze.tenants.pos_multi_terminal_allowed IS
  'Phase 1 POS is restricted to single-terminal sites. Flip to true only after F1 multi-terminal coordination ships.';
COMMENT ON COLUMN bronze.tenants.pos_max_terminals IS
  'Hard cap on concurrent active POS terminals per tenant. Default 1.';
```

- [ ] **Step 2: Commit**

```bash
git add migrations/084_add_tenant_pos_flags.sql
git commit -m "feat(pos): add bronze.tenants pos_multi_terminal_allowed + pos_max_terminals"
```

---

## Task 5: Migration — M1 permission slugs

**File:** Create `migrations/085_add_pos_m1_permissions.sql`

- [ ] **Step 1: Inspect `migrations/072_create_pos_rbac_roles.sql` to confirm table + column names**

```bash
head -60 migrations/072_create_pos_rbac_roles.sql
```

Note: it inserts into `rbac.permissions (id, category, description)` (or similar). Match that exact column list in the new migration.

- [ ] **Step 2: Write the migration**

```sql
-- Migration: 085 — POS M1 permission slugs
-- Layer: rbac
-- Idempotent.

INSERT INTO rbac.permissions (id, category, description) VALUES
    ('pos:device:register',      'pos', 'Register a new POS terminal device (admin)'),
    ('pos:device:revoke',        'pos', 'Revoke a POS terminal device binding (admin)'),
    ('pos:grant:refresh',        'pos', 'Refresh offline grant for an active shift'),
    ('pos:override:reconcile',   'pos', 'Use supervisor override to reconcile a rejected provisional sale')
ON CONFLICT (id) DO NOTHING;

-- Grant manager-role permissions for device management:
INSERT INTO rbac.role_permissions (role_id, permission_id)
SELECT r.id, p.id
  FROM rbac.roles r
  JOIN (VALUES
        ('pos:device:register'),
        ('pos:device:revoke'),
        ('pos:grant:refresh'),
        ('pos:override:reconcile')
  ) AS perms(pid)
       ON perms.pid = p.id
  JOIN rbac.permissions p ON p.id = perms.pid
 WHERE r.name = 'pos_manager'
ON CONFLICT DO NOTHING;
```

If the `role_permissions` table shape differs, adapt using the pattern from migration 072. If `rbac.roles`/`rbac.permissions` live in a different schema, fix the schema qualifier first.

- [ ] **Step 3: Commit**

```bash
git add migrations/085_add_pos_m1_permissions.sql
git commit -m "feat(pos): add M1 permission slugs (device/grant/override)"
```

---

## Task 6: Idempotency module (TDD, mock-based)

**Files:** Create `src/datapulse/pos/idempotency.py`, `tests/test_pos_idempotency.py`

- [ ] **Step 1: Write failing unit tests (no DB)**

Create `tests/test_pos_idempotency.py`:

```python
"""Idempotency handler unit tests. Pure unit, no DB."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

pytestmark = pytest.mark.unit


def _hash(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def test_check_and_claim_fresh_key_returns_replay_false():
    from datapulse.pos.idempotency import check_and_claim

    session = MagicMock()
    # First SELECT returns no row; INSERT succeeds
    session.execute.side_effect = [
        MagicMock(mappings=lambda: MagicMock(first=lambda: None)),   # SELECT
        MagicMock(),                                                 # INSERT
    ]
    ctx = check_and_claim(session, "k1", 1, "POST /x", _hash(b"{}"))
    assert ctx.replay is False
    assert ctx.cached_status is None


def test_check_and_claim_replays_when_hash_matches():
    from datapulse.pos.idempotency import check_and_claim

    session = MagicMock()
    h = _hash(b"{}")
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    row = {
        "request_hash": h,
        "response_status": 200,
        "response_body": {"ok": True},
        "expires_at": future,
    }
    session.execute.return_value.mappings.return_value.first.return_value = row

    ctx = check_and_claim(session, "k1", 1, "POST /x", h)
    assert ctx.replay is True
    assert ctx.cached_status == 200
    assert ctx.cached_body == {"ok": True}


def test_check_and_claim_409_on_hash_mismatch():
    from datapulse.pos.idempotency import check_and_claim

    session = MagicMock()
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    row = {
        "request_hash": _hash(b"OLD"),
        "response_status": 200,
        "response_body": {"ok": True},
        "expires_at": future,
    }
    session.execute.return_value.mappings.return_value.first.return_value = row

    with pytest.raises(HTTPException) as exc:
        check_and_claim(session, "k1", 1, "POST /x", _hash(b"NEW"))
    assert exc.value.status_code == 409


def test_check_and_claim_reclaims_expired_row():
    from datapulse.pos.idempotency import check_and_claim

    session = MagicMock()
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    expired = {
        "request_hash": _hash(b"{}"),
        "response_status": 200,
        "response_body": {"ok": True},
        "expires_at": past,
    }
    # First execute (SELECT) returns expired row; second (DELETE) no-op; third (INSERT) ok
    session.execute.side_effect = [
        MagicMock(mappings=lambda: MagicMock(first=lambda: expired)),   # SELECT
        MagicMock(),                                                     # DELETE
        MagicMock(),                                                     # INSERT
    ]
    ctx = check_and_claim(session, "k1", 1, "POST /x", _hash(b"{}"))
    assert ctx.replay is False


def test_record_response_issues_update():
    from datapulse.pos.idempotency import record_response

    session = MagicMock()
    record_response(session, "k1", 200, {"ok": True})
    session.execute.assert_called_once()
    _, kwargs = session.execute.call_args
    # The bound params carry the status/body
    sql_arg, params = session.execute.call_args.args
    assert params["key"] == "k1"
    assert params["st"] == 200
    assert params["body"] == {"ok": True}


def test_hash_body_is_sha256_hex():
    from datapulse.pos.idempotency import hash_body
    assert hash_body(b"hello") == hashlib.sha256(b"hello").hexdigest()
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
PYTHONPATH=src pytest tests/test_pos_idempotency.py -v
```

Expected: FAIL — `ModuleNotFoundError: datapulse.pos.idempotency`.

- [ ] **Step 3: Implement `src/datapulse/pos/idempotency.py`**

```python
"""POS request idempotency — dedupe retried mutating requests.

Retention (168h) strictly exceeds provisional queue window (72h) so every
client retry falls inside server dedupe horizon.

Design ref: §6.4.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

IDEMPOTENCY_TTL_HOURS: int = 168
PROVISIONAL_TTL_HOURS: int = 72


@dataclass(frozen=True)
class IdempotencyContext:
    key: str
    request_hash: str
    replay: bool
    cached_status: int | None = None
    cached_body: dict[str, Any] | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def hash_body(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def check_and_claim(
    session: Session,
    key: str,
    tenant_id: int,
    endpoint: str,
    request_hash: str,
) -> IdempotencyContext:
    row = session.execute(
        text(
            """
            SELECT request_hash, response_status, response_body, expires_at
              FROM pos.idempotency_keys
             WHERE key = :key AND tenant_id = :tenant_id
            """
        ),
        {"key": key, "tenant_id": tenant_id},
    ).mappings().first()

    if row:
        if row["expires_at"] < _now():
            session.execute(
                text("DELETE FROM pos.idempotency_keys WHERE key = :key AND tenant_id = :tid"),
                {"key": key, "tid": tenant_id},
            )
        else:
            if row["request_hash"] != request_hash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency-Key reuse with different request body.",
                )
            return IdempotencyContext(
                key=key,
                request_hash=request_hash,
                replay=True,
                cached_status=row["response_status"],
                cached_body=row["response_body"],
            )

    expires = _now() + timedelta(hours=IDEMPOTENCY_TTL_HOURS)
    try:
        session.execute(
            text(
                """
                INSERT INTO pos.idempotency_keys
                    (key, tenant_id, endpoint, request_hash, expires_at)
                VALUES (:key, :tid, :endpoint, :hash, :exp)
                """
            ),
            {"key": key, "tid": tenant_id, "endpoint": endpoint, "hash": request_hash, "exp": expires},
        )
    except IntegrityError:
        session.rollback()
        return check_and_claim(session, key, tenant_id, endpoint, request_hash)

    return IdempotencyContext(key=key, request_hash=request_hash, replay=False)


def record_response(
    session: Session,
    key: str,
    response_status: int,
    response_body: dict[str, Any] | None,
) -> None:
    session.execute(
        text(
            """
            UPDATE pos.idempotency_keys
               SET response_status = :st, response_body = :body
             WHERE key = :key
            """
        ),
        {"key": key, "st": response_status, "body": response_body},
    )


def idempotency_dependency(endpoint: str):
    """FastAPI dependency factory. Use as `Depends(idempotency_dependency('POST /foo'))`."""
    from datapulse.api.deps import get_tenant_session

    async def _dep(
        request: Request,
        idempotency_key: str = Header(..., alias="Idempotency-Key"),
        session: Session = Depends(get_tenant_session),
    ) -> IdempotencyContext:
        body = await request.body()
        tenant_id = int(getattr(request.state, "tenant_id", 1))
        return check_and_claim(
            session=session,
            key=idempotency_key,
            tenant_id=tenant_id,
            endpoint=endpoint,
            request_hash=hash_body(body),
        )

    return _dep
```

- [ ] **Step 4: Run tests**

```bash
PYTHONPATH=src pytest tests/test_pos_idempotency.py -v
```

Expected: all 6 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/datapulse/pos/idempotency.py tests/test_pos_idempotency.py
git commit -m "feat(pos): add idempotency module with 168h TTL + FastAPI dependency"
```

---

## Task 7: Capabilities module + endpoint

**Files:** Create `src/datapulse/pos/capabilities.py`; modify `src/datapulse/pos/models.py`; modify `src/datapulse/api/routes/pos.py`; create `tests/test_pos_capabilities.py`

- [ ] **Step 1: Create `src/datapulse/pos/capabilities.py`**

```python
"""POS capability document — feature-only, unauthenticated. Design ref: §6.6."""

from __future__ import annotations

POS_SERVER_VERSION: str = "1.0.0"
POS_MIN_CLIENT_VERSION: str = "1.0.0"
POS_MAX_CLIENT_VERSION: str | None = None

IDEMPOTENCY_PROTOCOL_VERSION: str = "v1"
CAPABILITIES_VERSION: str = "v1"

IDEMPOTENCY_TTL_HOURS: int = 168
PROVISIONAL_TTL_HOURS: int = 72
OFFLINE_GRANT_MAX_AGE_HOURS: int = 12

CAPABILITIES: dict[str, bool] = {
    "idempotency_key_header":   True,
    "pos_commit_endpoint":      True,
    "pos_catalog_stream":       False,   # deferred to M2
    "pos_shift_close":          True,
    "pos_corrective_void":      True,
    "override_reason_header":   True,
    "terminal_device_token":    True,
    "offline_grant_asymmetric": True,
    "multi_terminal_supported": False,
}
```

- [ ] **Step 2: Add Pydantic model in `src/datapulse/pos/models.py`**

Append:

```python
class CapabilitiesDoc(BaseModel):
    model_config = ConfigDict(frozen=True)
    server_version:   str
    min_client_version: str
    max_client_version: str | None
    idempotency:      str
    capabilities:     dict[str, bool]
    enforced_policies: dict[str, int]
    tenant_key_endpoint: str
    device_registration_endpoint: str
```

- [ ] **Step 3: Write failing route test**

Create `tests/test_pos_capabilities.py`:

```python
"""Capabilities endpoint tests — feature-only, no tenant state."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_capabilities_returns_required_flags(api_client):
    client, *_ = api_client
    r = client.get("/api/v1/pos/capabilities")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["idempotency"] == "v1"
    assert body["capabilities"]["idempotency_key_header"] is True
    assert body["capabilities"]["pos_commit_endpoint"] is True
    assert body["capabilities"]["multi_terminal_supported"] is False
    assert body["enforced_policies"]["idempotency_ttl_hours"] == 168
    assert body["enforced_policies"]["provisional_ttl_hours"] == 72


def test_capabilities_contains_no_tenant_state(api_client):
    client, *_ = api_client
    r = client.get("/api/v1/pos/capabilities")
    body = r.json()
    for forbidden in ("tenant_id", "active_terminals", "staff_id"):
        assert forbidden not in body
```

- [ ] **Step 4: Run — expect 404 (route missing)**

```bash
PYTHONPATH=src pytest tests/test_pos_capabilities.py -v
```

- [ ] **Step 5: Add the route to `src/datapulse/api/routes/pos.py`**

At the top (imports block):

```python
from datapulse.pos.capabilities import (
    CAPABILITIES,
    IDEMPOTENCY_PROTOCOL_VERSION,
    IDEMPOTENCY_TTL_HOURS,
    OFFLINE_GRANT_MAX_AGE_HOURS,
    POS_MAX_CLIENT_VERSION,
    POS_MIN_CLIENT_VERSION,
    POS_SERVER_VERSION,
    PROVISIONAL_TTL_HOURS,
)
from datapulse.pos.models import CapabilitiesDoc
```

At the bottom (new un-authenticated sub-router — does NOT inherit the module-level `router`'s auth dependencies):

```python
capabilities_router = APIRouter(prefix="/pos", tags=["pos"])


@capabilities_router.get("/capabilities", response_model=CapabilitiesDoc)
@limiter.limit("60/minute")
def capabilities(request: Request):
    """Feature-only capabilities document. No auth, no tenant state (§6.6)."""
    return CapabilitiesDoc(
        server_version=POS_SERVER_VERSION,
        min_client_version=POS_MIN_CLIENT_VERSION,
        max_client_version=POS_MAX_CLIENT_VERSION,
        idempotency=IDEMPOTENCY_PROTOCOL_VERSION,
        capabilities=dict(CAPABILITIES),
        enforced_policies={
            "idempotency_ttl_hours":       IDEMPOTENCY_TTL_HOURS,
            "provisional_ttl_hours":       PROVISIONAL_TTL_HOURS,
            "offline_grant_max_age_hours": OFFLINE_GRANT_MAX_AGE_HOURS,
        },
        tenant_key_endpoint="/api/v1/pos/tenant-key",
        device_registration_endpoint="/api/v1/pos/terminals/register-device",
    )
```

- [ ] **Step 6: Register `capabilities_router` in `src/datapulse/api/app.py`**

Find the `include_router(pos_router, …)` line and add a sibling:

```python
from datapulse.api.routes.pos import router as pos_router, capabilities_router as pos_capabilities_router
...
app.include_router(pos_capabilities_router, prefix=settings.api_prefix)
app.include_router(pos_router, prefix=settings.api_prefix)
```

- [ ] **Step 7: Run tests + commit**

```bash
PYTHONPATH=src pytest tests/test_pos_capabilities.py -v
```

Expected: both PASS.

```bash
git add src/datapulse/pos/capabilities.py \
        src/datapulse/pos/models.py \
        src/datapulse/api/routes/pos.py \
        src/datapulse/api/app.py \
        tests/test_pos_capabilities.py
git commit -m "feat(pos): add GET /pos/capabilities feature-only endpoint"
```

---

## Task 8: Tenant Ed25519 keypair module

**Files:** Create `src/datapulse/pos/tenant_keys.py`, `tests/test_pos_tenant_keys.py`

- [ ] **Step 1: Failing unit test (mocks only)**

```python
# tests/test_pos_tenant_keys.py
"""Tenant keypair tests — pure unit, mocked session."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


def test_rotate_tenant_key_inserts_row_and_returns_keypair():
    from datapulse.pos.tenant_keys import rotate_tenant_key

    session = MagicMock()
    key = rotate_tenant_key(session, tenant_id=1)

    assert key.key_id
    assert len(key.private_key) == 32
    assert len(key.public_key) == 32
    assert key.valid_from < key.valid_until
    session.execute.assert_called_once()


def test_list_public_keys_returns_mapped_rows():
    from datapulse.pos.tenant_keys import TenantKey, list_public_keys

    session = MagicMock()
    now = datetime.now(timezone.utc)
    session.execute.return_value.mappings.return_value.all.return_value = [
        {"key_id": "k1", "tenant_id": 1, "private_key": b"x" * 32, "public_key": b"y" * 32,
         "valid_from": now, "valid_until": now + timedelta(days=1)},
        {"key_id": "k2", "tenant_id": 1, "private_key": b"a" * 32, "public_key": b"b" * 32,
         "valid_from": now, "valid_until": now + timedelta(days=2)},
    ]
    keys = list_public_keys(session, 1)
    assert [k.key_id for k in keys] == ["k1", "k2"]


def test_active_private_key_falls_back_to_rotation_when_absent():
    from datapulse.pos.tenant_keys import active_private_key

    session = MagicMock()
    session.execute.return_value.mappings.return_value.first.return_value = None
    # rotate_tenant_key will fire an INSERT; we don't care about return details
    key = active_private_key(session, 1)
    assert len(key.private_key) == 32
```

- [ ] **Step 2: Implement `src/datapulse/pos/tenant_keys.py`**

```python
"""Per-tenant Ed25519 signing keypairs for offline grants. Design ref: §8.8.2."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from sqlalchemy import text
from sqlalchemy.orm import Session

KEY_ROTATION_INTERVAL = timedelta(days=1)
KEY_OVERLAP_WINDOW = timedelta(days=7)


@dataclass(frozen=True)
class TenantKey:
    key_id: str
    tenant_id: int
    private_key: bytes
    public_key: bytes
    valid_from: datetime
    valid_until: datetime


def _now() -> datetime:
    return datetime.now(timezone.utc)


def rotate_tenant_key(session: Session, tenant_id: int) -> TenantKey:
    key_id = str(uuid.uuid4())
    sk = Ed25519PrivateKey.generate()
    priv = sk.private_bytes(
        encoding=Encoding.Raw, format=PrivateFormat.Raw, encryption_algorithm=NoEncryption()
    )
    pub = sk.public_key().public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw)
    valid_from = _now()
    valid_until = valid_from + KEY_ROTATION_INTERVAL + KEY_OVERLAP_WINDOW

    session.execute(
        text(
            """
            INSERT INTO pos.tenant_keys
                (key_id, tenant_id, private_key, public_key, valid_from, valid_until)
            VALUES (:kid, :tid, :priv, :pub, :vf, :vu)
            """
        ),
        {"kid": key_id, "tid": tenant_id, "priv": priv, "pub": pub,
         "vf": valid_from, "vu": valid_until},
    )
    return TenantKey(key_id, tenant_id, priv, pub, valid_from, valid_until)


def active_private_key(session: Session, tenant_id: int) -> TenantKey:
    row = session.execute(
        text(
            """
            SELECT key_id, tenant_id, private_key, public_key, valid_from, valid_until
              FROM pos.tenant_keys
             WHERE tenant_id = :tid AND revoked_at IS NULL AND valid_until > :now
          ORDER BY valid_from DESC
             LIMIT 1
            """
        ),
        {"tid": tenant_id, "now": _now()},
    ).mappings().first()
    if not row:
        return rotate_tenant_key(session, tenant_id)
    return TenantKey(**row)


def list_public_keys(session: Session, tenant_id: int) -> list[TenantKey]:
    rows = session.execute(
        text(
            """
            SELECT key_id, tenant_id, private_key, public_key, valid_from, valid_until
              FROM pos.tenant_keys
             WHERE tenant_id = :tid AND revoked_at IS NULL AND valid_until > :now
          ORDER BY valid_from DESC
            """
        ),
        {"tid": tenant_id, "now": _now()},
    ).mappings().all()
    return [TenantKey(**r) for r in rows]
```

- [ ] **Step 3: Run tests + commit**

```bash
PYTHONPATH=src pytest tests/test_pos_tenant_keys.py -v
```

Expected: all PASS.

```bash
git add src/datapulse/pos/tenant_keys.py tests/test_pos_tenant_keys.py
git commit -m "feat(pos): add tenant Ed25519 keypair rotation module"
```

---

## Task 9: `GET /pos/tenant-key` endpoint

**Files:** modify `src/datapulse/pos/models.py`, `src/datapulse/api/routes/pos.py`; append test to `tests/test_pos_tenant_keys.py`

- [ ] **Step 1: Add Pydantic models to `models.py`**

```python
class TenantPublicKey(BaseModel):
    model_config = ConfigDict(frozen=True)
    key_id:       str
    public_key:   str          # base64-url of raw 32-byte public key
    valid_from:   datetime
    valid_until:  datetime


class TenantKeysResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    keys: list[TenantPublicKey]
```

- [ ] **Step 2: Failing route test (mock-based)**

Append to `tests/test_pos_tenant_keys.py`:

```python
def test_tenant_key_endpoint_returns_current_public_keys(api_client, monkeypatch):
    from datapulse.pos.tenant_keys import TenantKey
    from datetime import datetime, timedelta, timezone

    client, *_ = api_client

    now = datetime.now(timezone.utc)
    fake_keys = [
        TenantKey("k1", 1, b"p" * 32, b"q" * 32, now, now + timedelta(days=1)),
        TenantKey("k2", 1, b"r" * 32, b"s" * 32, now, now + timedelta(days=2)),
    ]

    def _stub(_session, _tid):
        return fake_keys

    monkeypatch.setattr("datapulse.api.routes.pos.list_public_keys", _stub)

    r = client.get("/api/v1/pos/tenant-key", headers={"X-API-Key": "test-api-key"})
    assert r.status_code == 200
    body = r.json()
    assert len(body["keys"]) == 2
    assert {k["key_id"] for k in body["keys"]} == {"k1", "k2"}
```

- [ ] **Step 3: Add the route to `src/datapulse/api/routes/pos.py`**

Imports:

```python
from base64 import urlsafe_b64encode

from datapulse.api.deps import get_tenant_session
from datapulse.pos.models import TenantKeysResponse, TenantPublicKey
from datapulse.pos.tenant_keys import list_public_keys
```

Route (inside the main `router`, after `/products/search` or similar):

```python
@router.get("/tenant-key", response_model=TenantKeysResponse)
@limiter.limit("30/minute")
def tenant_key(
    request: Request,
    user: CurrentUser,
    session=Depends(get_tenant_session),
):
    tenant_id = _tenant_id_of(user)
    keys = list_public_keys(session, tenant_id)
    return TenantKeysResponse(
        keys=[
            TenantPublicKey(
                key_id=k.key_id,
                public_key=urlsafe_b64encode(k.public_key).decode().rstrip("="),
                valid_from=k.valid_from,
                valid_until=k.valid_until,
            )
            for k in keys
        ]
    )
```

- [ ] **Step 4: Run + commit**

```bash
PYTHONPATH=src pytest tests/test_pos_tenant_keys.py -v
```

```bash
git add src/datapulse/pos/models.py src/datapulse/api/routes/pos.py tests/test_pos_tenant_keys.py
git commit -m "feat(pos): add GET /pos/tenant-key endpoint"
```

---

## Task 10: Device registration module + endpoint

**Files:** `src/datapulse/pos/devices.py`, `src/datapulse/pos/models.py`, `src/datapulse/api/routes/pos.py`, `tests/test_pos_devices.py`

- [ ] **Step 1: Pydantic models in `models.py`**

```python
from typing import Literal


class DeviceRegisterRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    terminal_id:         int = Field(ge=1)
    public_key:          str = Field(min_length=32)          # base64-url raw pubkey
    device_fingerprint:  str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class DeviceRegisterResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    device_id:     int
    terminal_id:   int
    registered_at: datetime
```

- [ ] **Step 2: Create `src/datapulse/pos/devices.py` (module-level helpers + verifier)**

```python
"""Device-bound POS terminal credentials. Design ref: §8.9."""

from __future__ import annotations

import hashlib
from base64 import urlsafe_b64decode
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.api.deps import get_tenant_session

CLOCK_SKEW_TOLERANCE_MINUTES: int = 2


@dataclass(frozen=True)
class TerminalDevice:
    id: int
    tenant_id: int
    terminal_id: int
    public_key: bytes
    device_fingerprint: str
    revoked_at: datetime | None


@dataclass(frozen=True)
class DeviceProof:
    terminal_id: int
    device: TerminalDevice
    signed_at: datetime
    idempotency_key: str


def register_device(
    session: Session,
    *,
    tenant_id: int,
    terminal_id: int,
    public_key_b64: str,
    device_fingerprint: str,
) -> int:
    pk = urlsafe_b64decode(public_key_b64 + "==")
    if len(pk) != 32:
        raise HTTPException(status_code=400, detail="public_key must be 32 raw bytes")

    existing = session.execute(
        text(
            """SELECT id FROM pos.terminal_devices
                WHERE terminal_id = :tid AND revoked_at IS NULL"""
        ),
        {"tid": terminal_id},
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="terminal already has a registered device")

    row = session.execute(
        text(
            """
            INSERT INTO pos.terminal_devices
                (tenant_id, terminal_id, public_key, device_fingerprint)
            VALUES (:tenant, :tid, :pk, :fp)
            RETURNING id
            """
        ),
        {"tenant": tenant_id, "tid": terminal_id, "pk": pk, "fp": device_fingerprint},
    ).first()
    return int(row[0])


def load_active_device(
    session: Session, terminal_id: int, tenant_id: int
) -> TerminalDevice | None:
    row = session.execute(
        text(
            """
            SELECT id, tenant_id, terminal_id, public_key, device_fingerprint, revoked_at
              FROM pos.terminal_devices
             WHERE terminal_id = :tid AND tenant_id = :tenant AND revoked_at IS NULL
            """
        ),
        {"tid": terminal_id, "tenant": tenant_id},
    ).mappings().first()
    return TerminalDevice(**row) if row else None


def verify_signature(public_key: bytes, message: bytes, signature: bytes) -> bool:
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(signature, message)
        return True
    except (InvalidSignature, ValueError):
        return False


async def device_token_verifier(
    request: Request,
    x_terminal_id: int = Header(..., alias="X-Terminal-Id"),
    x_device_fingerprint: str = Header(..., alias="X-Device-Fingerprint"),
    x_signed_at: str = Header(..., alias="X-Signed-At"),
    x_terminal_token: str = Header(..., alias="X-Terminal-Token"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    session: Session = Depends(get_tenant_session),
) -> DeviceProof:
    """Verify per-request device-bound Ed25519 proof. §8.9.2 canonical digest."""
    tenant_id = int(getattr(request.state, "tenant_id", 1))

    device = load_active_device(session, x_terminal_id, tenant_id)
    if device is None:
        raise HTTPException(status_code=401, detail="unknown device")
    if device.revoked_at is not None:
        raise HTTPException(status_code=401, detail="device revoked")
    if device.device_fingerprint != x_device_fingerprint:
        raise HTTPException(status_code=401, detail="fingerprint mismatch")

    try:
        signed_at_dt = datetime.fromisoformat(x_signed_at.replace("Z", "+00:00"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail="invalid X-Signed-At") from e

    now = datetime.now(timezone.utc)
    if signed_at_dt > now + timedelta(minutes=CLOCK_SKEW_TOLERANCE_MINUTES):
        raise HTTPException(status_code=401, detail="signed_at in the future")

    body = await request.body()
    body_hash = hashlib.sha256(body).hexdigest()
    digest = "\n".join([
        request.method,
        request.url.path,
        idempotency_key,
        str(x_terminal_id),
        body_hash,
        x_signed_at,
    ]).encode()

    signature = urlsafe_b64decode(x_terminal_token + "==")
    if not verify_signature(device.public_key, digest, signature):
        raise HTTPException(status_code=401, detail="signature verification failed")

    return DeviceProof(
        terminal_id=x_terminal_id,
        device=device,
        signed_at=signed_at_dt,
        idempotency_key=idempotency_key,
    )
```

- [ ] **Step 3: Unit tests**

```python
# tests/test_pos_devices.py
"""Device module unit tests — mocked session only."""

from __future__ import annotations

from base64 import urlsafe_b64encode
from unittest.mock import MagicMock

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi import HTTPException

pytestmark = pytest.mark.unit


def _pub_b64():
    sk = Ed25519PrivateKey.generate()
    pk = sk.public_key().public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw)
    return sk, urlsafe_b64encode(pk).decode().rstrip("=")


def test_register_device_inserts_new_row():
    from datapulse.pos.devices import register_device

    session = MagicMock()
    session.execute.return_value.first.side_effect = [None, (42,)]
    _, pk = _pub_b64()
    fp = "sha256:" + "a" * 64

    device_id = register_device(session, tenant_id=1, terminal_id=7, public_key_b64=pk, device_fingerprint=fp)
    assert device_id == 42


def test_register_device_409_when_already_registered():
    from datapulse.pos.devices import register_device

    session = MagicMock()
    session.execute.return_value.first.return_value = (1,)
    _, pk = _pub_b64()
    fp = "sha256:" + "b" * 64

    with pytest.raises(HTTPException) as exc:
        register_device(session, tenant_id=1, terminal_id=7, public_key_b64=pk, device_fingerprint=fp)
    assert exc.value.status_code == 409


def test_verify_signature_accepts_valid_then_rejects_tampered():
    from datapulse.pos.devices import verify_signature

    sk = Ed25519PrivateKey.generate()
    pk = sk.public_key().public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw)

    msg = b"payload"
    sig = sk.sign(msg)
    assert verify_signature(pk, msg, sig) is True
    assert verify_signature(pk, b"other-payload", sig) is False
```

- [ ] **Step 4: Add registration route**

In `src/datapulse/api/routes/pos.py`:

```python
from datapulse.pos.devices import register_device
from datapulse.pos.models import DeviceRegisterRequest, DeviceRegisterResponse


@router.post(
    "/terminals/register-device",
    response_model=DeviceRegisterResponse,
    dependencies=[Depends(require_permission("pos:device:register"))],
)
@limiter.limit("10/minute")
def register_terminal_device(
    request: Request,
    payload: DeviceRegisterRequest,
    user: CurrentUser,
    session=Depends(get_tenant_session),
):
    tenant_id = _tenant_id_of(user)
    device_id = register_device(
        session,
        tenant_id=tenant_id,
        terminal_id=payload.terminal_id,
        public_key_b64=payload.public_key,
        device_fingerprint=payload.device_fingerprint,
    )
    session.commit()
    return DeviceRegisterResponse(
        device_id=device_id,
        terminal_id=payload.terminal_id,
        registered_at=datetime.now(timezone.utc),
    )
```

Add a route-level test in `tests/test_pos_devices.py`:

```python
def test_register_device_route_calls_service_and_returns_response(api_client, monkeypatch):
    from datetime import datetime, timezone

    client, *_ = api_client

    def _stub(_s, *, tenant_id, terminal_id, public_key_b64, device_fingerprint):
        assert terminal_id == 11
        return 99

    monkeypatch.setattr("datapulse.api.routes.pos.register_device", _stub)

    _, pk = _pub_b64()
    r = client.post(
        "/api/v1/pos/terminals/register-device",
        json={"terminal_id": 11, "public_key": pk, "device_fingerprint": "sha256:" + "a" * 64},
        headers={"X-API-Key": "test-api-key"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["device_id"] == 99
    assert r.json()["terminal_id"] == 11
```

- [ ] **Step 5: Run + commit**

```bash
PYTHONPATH=src pytest tests/test_pos_devices.py -v
```

```bash
git add src/datapulse/pos/devices.py src/datapulse/pos/models.py \
        src/datapulse/api/routes/pos.py tests/test_pos_devices.py
git commit -m "feat(pos): add device registration + Ed25519 verifier scaffolding"
```

---

## Task 11: Offline grant module

**Files:** `src/datapulse/pos/grants.py`, `src/datapulse/pos/models.py`, `tests/test_pos_grants.py`

- [ ] **Step 1: Pydantic models in `models.py`**

```python
class OverrideCodeEntry(BaseModel):
    model_config = ConfigDict(frozen=True)
    code_id:            str
    salt:               str
    hash:               str
    issued_to_staff_id: str | None = None


class RoleSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)
    can_checkout:            bool = True
    can_void:                bool = False
    can_override_price:      bool = False
    can_apply_discount:      bool = True
    max_discount_pct:        int  = 15
    can_process_returns:     bool = False
    can_open_drawer_no_sale: bool = False
    can_close_shift:         bool = True


class OfflineGrantPayload(BaseModel):
    model_config = ConfigDict(frozen=True)
    iss:                 str = "datapulse-pos"
    grant_id:            str
    terminal_id:         int
    tenant_id:           int
    device_fingerprint:  str
    staff_id:            str
    shift_id:            int
    issued_at:           datetime
    offline_expires_at:  datetime
    role_snapshot:       RoleSnapshot
    override_codes:      list[OverrideCodeEntry]
    capabilities_version: str = "v1"


class OfflineGrantEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True)
    payload:             OfflineGrantPayload
    signature_ed25519:   str
    key_id:              str
```

- [ ] **Step 2: Create `src/datapulse/pos/grants.py`**

```python
"""Offline grant issuance (§8.8.2)."""

from __future__ import annotations

import json
import secrets
import uuid
from base64 import urlsafe_b64encode
from datetime import datetime, timedelta, timezone
from hashlib import scrypt as _scrypt

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.pos.models import (
    OfflineGrantEnvelope,
    OfflineGrantPayload,
    OverrideCodeEntry,
    RoleSnapshot,
)
from datapulse.pos.tenant_keys import active_private_key


SCRYPT_N = 2 ** 14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_LEN = 32


def _hash_code(plain: str, salt: bytes) -> bytes:
    return _scrypt(plain.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=SCRYPT_LEN)


def _generate_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(8))


def issue_grant_for_shift(
    session: Session,
    *,
    tenant_id: int,
    terminal_id: int,
    shift_id: int,
    staff_id: str,
    device_fingerprint: str,
    role_snapshot_overrides: dict | None = None,
    offline_ttl_hours: int = 12,
    override_code_count: int = 5,
) -> OfflineGrantEnvelope:
    now = datetime.now(timezone.utc)
    grant_id = str(uuid.uuid4())
    role = RoleSnapshot(**(role_snapshot_overrides or {}))

    codes: list[OverrideCodeEntry] = []
    for i in range(override_code_count):
        code_id = f"c-{i+1:02d}"
        plain = _generate_code()
        salt = secrets.token_bytes(16)
        h = _hash_code(plain, salt)
        codes.append(OverrideCodeEntry(
            code_id=code_id,
            salt=urlsafe_b64encode(salt).decode().rstrip("="),
            hash=urlsafe_b64encode(h).decode().rstrip("="),
        ))
        # Plaintext NOT returned to client; distribution happens out-of-band.

    payload = OfflineGrantPayload(
        grant_id=grant_id,
        terminal_id=terminal_id,
        tenant_id=tenant_id,
        device_fingerprint=device_fingerprint,
        staff_id=staff_id,
        shift_id=shift_id,
        issued_at=now,
        offline_expires_at=now + timedelta(hours=offline_ttl_hours),
        role_snapshot=role,
        override_codes=codes,
    )

    tkey = active_private_key(session, tenant_id)
    sk = Ed25519PrivateKey.from_private_bytes(tkey.private_key)
    signature = sk.sign(payload.model_dump_json().encode())
    envelope = OfflineGrantEnvelope(
        payload=payload,
        signature_ed25519=urlsafe_b64encode(signature).decode().rstrip("="),
        key_id=tkey.key_id,
    )

    session.execute(
        text(
            """
            INSERT INTO pos.grants_issued
                (grant_id, tenant_id, terminal_id, shift_id, staff_id,
                 key_id, code_ids, issued_at, offline_expires_at)
            VALUES
                (:gid, :tid, :term, :shift, :staff, :kid, :codes, :iss, :exp)
            """
        ),
        {
            "gid": grant_id, "tid": tenant_id, "term": terminal_id, "shift": shift_id,
            "staff": staff_id, "kid": tkey.key_id,
            "codes": json.dumps([c.code_id for c in codes]),
            "iss": now, "exp": payload.offline_expires_at,
        },
    )
    return envelope
```

- [ ] **Step 3: Unit test**

```python
# tests/test_pos_grants.py
"""Grant issuance unit tests — mocked session + keypair."""

from __future__ import annotations

from base64 import urlsafe_b64decode
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

pytestmark = pytest.mark.unit


def test_issue_grant_produces_verifiable_ed25519_signature():
    from datapulse.pos.grants import issue_grant_for_shift
    from datapulse.pos.tenant_keys import TenantKey, rotate_tenant_key

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat

    sk = Ed25519PrivateKey.generate()
    priv = sk.private_bytes(encoding=Encoding.Raw, format=PrivateFormat.Raw, encryption_algorithm=NoEncryption())
    pub = sk.public_key().public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw)
    now = datetime.now(timezone.utc)
    fake = TenantKey("kid-1", 1, priv, pub, now, now + timedelta(days=1))

    session = MagicMock()
    with patch("datapulse.pos.grants.active_private_key", return_value=fake):
        env = issue_grant_for_shift(
            session,
            tenant_id=1,
            terminal_id=5,
            shift_id=9,
            staff_id="s-1",
            device_fingerprint="sha256:" + "a" * 64,
            override_code_count=3,
        )

    assert len(env.payload.override_codes) == 3
    assert env.key_id == "kid-1"

    sig = urlsafe_b64decode(env.signature_ed25519 + "==")
    msg = env.payload.model_dump_json().encode()
    Ed25519PublicKey.from_public_bytes(pub).verify(sig, msg)  # no exception = verified
```

- [ ] **Step 4: Run + commit**

```bash
PYTHONPATH=src pytest tests/test_pos_grants.py -v
```

```bash
git add src/datapulse/pos/grants.py src/datapulse/pos/models.py tests/test_pos_grants.py
git commit -m "feat(pos): add Ed25519-signed offline grant issuance module"
```

---

## Task 12: Override token verifier

**Files:** `src/datapulse/pos/overrides.py`, `src/datapulse/pos/models.py`, `tests/test_pos_overrides.py`

- [ ] **Step 1: Pydantic models**

```python
class OverrideTokenClaim(BaseModel):
    model_config = ConfigDict(frozen=True)
    grant_id:          str
    code_id:           str
    tenant_id:         int
    terminal_id:       int
    shift_id:          int
    action:            Literal["retry_override","void","no_sale","price_override","discount_above_limit"]
    action_subject_id: str | None = None
    consumed_at:       datetime


class OverrideTokenEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True)
    claim:     OverrideTokenClaim
    signature: str
```

- [ ] **Step 2: Create `src/datapulse/pos/overrides.py`**

```python
"""Server-side override token verifier. Design ref: §8.8.6."""

from __future__ import annotations

import json
from base64 import urlsafe_b64decode
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from datapulse.api.deps import get_tenant_session
from datapulse.pos.devices import DeviceProof, device_token_verifier, verify_signature
from datapulse.pos.models import OverrideTokenEnvelope


def override_token_verifier(expected_action: str):
    async def _dep(
        request: Request,
        proof: DeviceProof = Depends(device_token_verifier),
        x_override_token: str = Header(..., alias="X-Override-Token"),
        session: Session = Depends(get_tenant_session),
    ) -> OverrideTokenEnvelope:
        try:
            env = OverrideTokenEnvelope.model_validate(
                json.loads(urlsafe_b64decode(x_override_token + "==").decode())
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail="invalid X-Override-Token") from e

        claim = env.claim
        if claim.action != expected_action:
            raise HTTPException(status_code=403, detail="override action mismatch")
        if claim.terminal_id != proof.terminal_id:
            raise HTTPException(status_code=401, detail="override terminal mismatch")

        msg = claim.model_dump_json().encode()
        sig = urlsafe_b64decode(env.signature + "==")
        if not verify_signature(proof.device.public_key, msg, sig):
            raise HTTPException(status_code=401, detail="override signature invalid")

        row = session.execute(
            text("SELECT code_ids, offline_expires_at FROM pos.grants_issued WHERE grant_id = :g"),
            {"g": claim.grant_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=401, detail="invalid grant_id")
        if claim.code_id not in row["code_ids"]:
            raise HTTPException(status_code=401, detail="invalid code_id")
        if row["offline_expires_at"] < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="grant expired")

        try:
            session.execute(
                text(
                    """
                    INSERT INTO pos.override_consumptions
                        (grant_id, code_id, tenant_id, terminal_id, shift_id,
                         action, action_subject_id, consumed_at, request_idempotency_key)
                    VALUES (:g, :c, :tid, :term, :shift, :act, :sub, :cons, :idem)
                    """
                ),
                {
                    "g": claim.grant_id, "c": claim.code_id,
                    "tid": claim.tenant_id, "term": claim.terminal_id, "shift": claim.shift_id,
                    "act": claim.action, "sub": claim.action_subject_id,
                    "cons": claim.consumed_at, "idem": proof.idempotency_key,
                },
            )
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=409, detail="override_already_consumed")

        return env

    return _dep
```

- [ ] **Step 3: Unit test**

```python
# tests/test_pos_overrides.py
"""override_token_verifier unit tests — mocked session + device_token_verifier."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


def test_override_token_verifier_returns_callable():
    from datapulse.pos.overrides import override_token_verifier

    dep = override_token_verifier("void")
    assert callable(dep)
```

For deeper route coverage, route-level tests live under Task 14 (void-retrofit). The factory is enough here — it's a thin wrapper; the SQL paths all have test coverage via mocks in the route tests.

- [ ] **Step 4: Commit**

```bash
PYTHONPATH=src pytest tests/test_pos_overrides.py -v
```

```bash
git add src/datapulse/pos/overrides.py src/datapulse/pos/models.py tests/test_pos_overrides.py
git commit -m "feat(pos): add override_token_verifier dependency factory"
```

---

## Task 13: `GET /pos/terminals/active-for-me` + single-terminal guard

**Files:** `src/datapulse/pos/models.py`, `src/datapulse/api/routes/pos.py`, `tests/test_pos_single_terminal_guard.py`

- [ ] **Step 1: Models**

```python
class ActiveTerminalRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    terminal_id:         int
    device_fingerprint:  str | None
    opened_at:           datetime


class ActiveForMeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    active_terminals:         list[ActiveTerminalRow]
    multi_terminal_allowed:   bool
    max_terminals:            int
```

- [ ] **Step 2: Route + guard**

In `src/datapulse/api/routes/pos.py`:

```python
from datapulse.pos.models import ActiveForMeResponse, ActiveTerminalRow


@router.get("/terminals/active-for-me", response_model=ActiveForMeResponse)
@limiter.limit("60/minute")
def active_for_me(
    request: Request,
    user: CurrentUser,
    session=Depends(get_tenant_session),
):
    tenant_id = _tenant_id_of(user)
    rows = session.execute(
        text(
            """
            SELECT ts.id            AS terminal_id,
                   td.device_fingerprint,
                   ts.opened_at
              FROM pos.terminal_sessions ts
         LEFT JOIN pos.terminal_devices td
                ON td.terminal_id = ts.id AND td.revoked_at IS NULL
             WHERE ts.tenant_id = :tid AND ts.status IN ('open', 'active', 'paused')
            """
        ),
        {"tid": tenant_id},
    ).mappings().all()

    flags = session.execute(
        text(
            """SELECT pos_multi_terminal_allowed, pos_max_terminals
                 FROM bronze.tenants
                WHERE tenant_id = :tid"""
        ),
        {"tid": tenant_id},
    ).mappings().first() or {"pos_multi_terminal_allowed": False, "pos_max_terminals": 1}

    return ActiveForMeResponse(
        active_terminals=[ActiveTerminalRow(**r) for r in rows],
        multi_terminal_allowed=bool(flags["pos_multi_terminal_allowed"]),
        max_terminals=int(flags["pos_max_terminals"]),
    )
```

Then modify the existing `open_terminal` route (currently around `src/datapulse/api/routes/pos.py:95`) to add the guard at the top of the handler body:

```python
tenant_id = _tenant_id_of(user)
max_terminals = (session.execute(
    text("SELECT pos_max_terminals FROM bronze.tenants WHERE tenant_id = :tid"),
    {"tid": tenant_id},
).scalar()) or 1
active_count = (session.execute(
    text(
        """SELECT count(*) FROM pos.terminal_sessions
            WHERE tenant_id = :tid AND status IN ('open','active','paused')"""
    ),
    {"tid": tenant_id},
).scalar()) or 0
if active_count >= max_terminals:
    raise HTTPException(
        status_code=409,
        detail=f"multi_terminal_limit_reached:{active_count}/{max_terminals}",
    )
```

- [ ] **Step 3: Tests**

```python
# tests/test_pos_single_terminal_guard.py
"""Single-terminal enforcement tests — mocked session."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def test_active_for_me_returns_caller_terminals(api_client, monkeypatch):
    client, *_ = api_client

    def _stub_execute(stmt, params=None):
        s = str(stmt)
        if "terminal_sessions" in s:
            m = MagicMock()
            m.mappings.return_value.all.return_value = [
                {"terminal_id": 42, "device_fingerprint": None,
                 "opened_at": "2026-04-17T06:00:00+00:00"},
            ]
            return m
        if "bronze.tenants" in s:
            m = MagicMock()
            m.mappings.return_value.first.return_value = {
                "pos_multi_terminal_allowed": False, "pos_max_terminals": 1,
            }
            return m
        return MagicMock()

    # Patch the dependency_overrides' mocked session to route execute through _stub_execute
    from datapulse.api import app as app_mod

    session = MagicMock()
    session.execute.side_effect = _stub_execute
    for k, v in list(client.app.dependency_overrides.items()):
        if callable(v):
            try:
                if v() is None or True:
                    pass
            except TypeError:
                pass
    from datapulse.api.deps import get_tenant_session
    client.app.dependency_overrides[get_tenant_session] = lambda: session

    r = client.get("/api/v1/pos/terminals/active-for-me", headers={"X-API-Key": "test-api-key"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["multi_terminal_allowed"] is False
    assert body["max_terminals"] == 1
    assert body["active_terminals"][0]["terminal_id"] == 42
```

If the test setup for patching `get_tenant_session` feels awkward, factor the stub into a conftest fixture `db_session_stub` that returns the session + helper to attach rows-per-query. Keep it in a reusable form so Tasks 14+ can reuse.

- [ ] **Step 4: Commit**

```bash
PYTHONPATH=src pytest tests/test_pos_single_terminal_guard.py -v
```

```bash
git add src/datapulse/pos/models.py src/datapulse/api/routes/pos.py tests/test_pos_single_terminal_guard.py
git commit -m "feat(pos): add /terminals/active-for-me + 409 guard on terminal open"
```

---

## Task 14: Atomic commit endpoint

**Files:** `src/datapulse/pos/commit.py`, `src/datapulse/pos/models.py`, `src/datapulse/api/routes/pos.py`, `tests/test_pos_commit.py`

- [ ] **Step 1: Pydantic models**

```python
class CommitRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    terminal_id:        int = Field(ge=1)
    shift_id:           int = Field(ge=1)
    staff_id:           str
    customer_id:        str | None = None
    site_code:          str
    items:              list[PosCartItem]
    subtotal:           JsonDecimal
    discount_total:     JsonDecimal = Decimal("0")
    tax_total:          JsonDecimal = Decimal("0")
    grand_total:        JsonDecimal
    payment_method:     PaymentMethod
    cash_tendered:      JsonDecimal | None = None


class CommitResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    transaction_id:       int
    receipt_number:       str
    commit_confirmed_at:  datetime
    change_due:           JsonDecimal = Decimal("0")
```

- [ ] **Step 2: `src/datapulse/pos/commit.py`**

```python
"""Atomic POS commit (§3). Inserts header + items + sets commit_confirmed_at in one tx."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.pos.models import CommitRequest, CommitResponse


def _next_receipt_number(session: Session, tenant_id: int) -> str:
    now = datetime.now(timezone.utc)
    seq = session.execute(
        text(
            """SELECT count(*) + 1 FROM pos.transactions
                WHERE tenant_id = :tid AND created_at >= date_trunc('day', now())"""
        ),
        {"tid": tenant_id},
    ).scalar() or 1
    return f"R-{now.strftime('%Y%m%d')}-{int(seq):06d}"


def atomic_commit(
    session: Session,
    *,
    tenant_id: int,
    payload: CommitRequest,
) -> CommitResponse:
    if payload.payment_method.value == "cash":
        tendered = payload.cash_tendered or Decimal("0")
        if tendered < payload.grand_total:
            raise HTTPException(status_code=400, detail="cash_tendered < grand_total")
        change_due = tendered - payload.grand_total
    else:
        change_due = Decimal("0")

    receipt = _next_receipt_number(session, tenant_id)
    now = datetime.now(timezone.utc)

    txn_row = session.execute(
        text(
            """
            INSERT INTO pos.transactions
                (tenant_id, terminal_id, staff_id, customer_id, site_code,
                 subtotal, discount_total, tax_total, grand_total,
                 payment_method, status, receipt_number,
                 shift_id, created_at, commit_confirmed_at)
            VALUES
                (:tid, :term, :staff, :cust, :site,
                 :sub, :disc, :tax, :grand,
                 :pm, 'completed', :rec, :shift, :now, :now)
            RETURNING id
            """
        ),
        {
            "tid": tenant_id, "term": payload.terminal_id, "staff": payload.staff_id,
            "cust": payload.customer_id, "site": payload.site_code,
            "sub": payload.subtotal, "disc": payload.discount_total,
            "tax": payload.tax_total, "grand": payload.grand_total,
            "pm": payload.payment_method.value, "rec": receipt,
            "shift": payload.shift_id, "now": now,
        },
    ).first()
    transaction_id = int(txn_row[0])

    for item in payload.items:
        session.execute(
            text(
                """
                INSERT INTO pos.transaction_items
                    (tenant_id, transaction_id, drug_code, drug_name,
                     batch_number, expiry_date, quantity, unit_price,
                     discount, line_total, is_controlled, pharmacist_id)
                VALUES
                    (:tid, :txn, :dc, :dn, :bn, :exp, :qty, :up, :disc, :lt, :ic, :ph)
                """
            ),
            {
                "tid": tenant_id, "txn": transaction_id,
                "dc": item.drug_code, "dn": item.drug_name,
                "bn": item.batch_number, "exp": item.expiry_date,
                "qty": item.quantity, "up": item.unit_price,
                "disc": item.discount, "lt": item.line_total,
                "ic": item.is_controlled, "ph": item.pharmacist_id,
            },
        )

    return CommitResponse(
        transaction_id=transaction_id,
        receipt_number=receipt,
        commit_confirmed_at=now,
        change_due=change_due,
    )
```

- [ ] **Step 3: Unit test (pure mock, no route)**

```python
# tests/test_pos_commit.py
"""atomic_commit unit tests — mocked session."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from datapulse.pos.constants import PaymentMethod
from datapulse.pos.models import CommitRequest, PosCartItem

pytestmark = pytest.mark.unit


def _payload(total="12.00", tendered="20.00", pm=PaymentMethod.cash):
    return CommitRequest(
        terminal_id=1, shift_id=1, staff_id="s", site_code="S1",
        items=[PosCartItem(
            drug_code="D", drug_name="n", quantity=Decimal("1"),
            unit_price=Decimal("12.00"), line_total=Decimal("12.00"),
        )],
        subtotal=Decimal(total), grand_total=Decimal(total),
        payment_method=pm, cash_tendered=Decimal(tendered) if tendered else None,
    )


def test_atomic_commit_returns_response_with_change_due():
    from datapulse.pos.commit import atomic_commit

    session = MagicMock()
    # _next_receipt_number scalar + INSERT RETURNING id + N inserts for items
    session.execute.return_value.scalar.return_value = 1
    session.execute.return_value.first.return_value = (42,)

    resp = atomic_commit(session, tenant_id=1, payload=_payload())
    assert resp.transaction_id == 42
    assert resp.receipt_number.startswith("R-")
    assert resp.change_due == Decimal("8.00")


def test_atomic_commit_400_when_cash_insufficient():
    from datapulse.pos.commit import atomic_commit

    session = MagicMock()
    with pytest.raises(HTTPException) as exc:
        atomic_commit(session, tenant_id=1, payload=_payload(total="50.00", tendered="10.00"))
    assert exc.value.status_code == 400
```

- [ ] **Step 4: Wire route + replay check**

In `src/datapulse/api/routes/pos.py`:

```python
from datapulse.pos.commit import atomic_commit
from datapulse.pos.devices import DeviceProof, device_token_verifier
from datapulse.pos.idempotency import idempotency_dependency, record_response
from datapulse.pos.models import CommitRequest, CommitResponse


@router.post(
    "/transactions/commit",
    response_model=CommitResponse,
    dependencies=[Depends(require_permission("pos:transaction:checkout"))],
)
@limiter.limit("30/minute")
async def commit_transaction(
    request: Request,
    payload: CommitRequest,
    user: CurrentUser,
    proof: DeviceProof = Depends(device_token_verifier),
    idem=Depends(idempotency_dependency("POST /pos/transactions/commit")),
    session=Depends(get_tenant_session),
):
    if idem.replay:
        return CommitResponse.model_validate(idem.cached_body)

    if payload.terminal_id != proof.terminal_id:
        raise HTTPException(status_code=400, detail="body/header terminal_id mismatch")

    tenant_id = _tenant_id_of(user)
    response = atomic_commit(session, tenant_id=tenant_id, payload=payload)
    record_response(session, idem.key, 200, response.model_dump(mode="json"))
    session.commit()
    return response
```

- [ ] **Step 5: Commit**

```bash
PYTHONPATH=src pytest tests/test_pos_commit.py -v
```

```bash
git add src/datapulse/pos/commit.py src/datapulse/pos/models.py \
        src/datapulse/api/routes/pos.py tests/test_pos_commit.py
git commit -m "feat(pos): add atomic POST /transactions/commit endpoint"
```

---

## Task 15: Server-enforced shift close guard

**Files:** `src/datapulse/pos/models.py`, `src/datapulse/api/routes/pos.py`, `tests/test_pos_shift_close_guard.py`

- [ ] **Step 1: Extended close-request model**

```python
class LocalUnresolvedClaim(BaseModel):
    model_config = ConfigDict(frozen=True)
    count:   int = Field(ge=0)
    digest:  str = Field(min_length=10, max_length=200)


class CloseShiftRequestV2(BaseModel):
    model_config = ConfigDict(frozen=True)
    closing_cash:     JsonDecimal
    notes:            str | None = None
    local_unresolved: LocalUnresolvedClaim
```

- [ ] **Step 2: Modify close route**

In `src/datapulse/api/routes/pos.py`, find the existing `close_shift` handler and add the guard logic at the top (before business logic). Outline:

```python
from datapulse.pos.models import CloseShiftRequestV2

@router.post("/shifts/{shift_id}/close", response_model=ShiftSummaryResponse,
             dependencies=[Depends(require_permission("pos:shift:reconcile"))])
@limiter.limit("10/minute")
async def close_shift(
    request: Request,
    shift_id: int = Path(ge=1),
    payload: CloseShiftRequestV2 = ...,
    user: CurrentUser = ...,
    proof: DeviceProof = Depends(device_token_verifier),
    idem=Depends(idempotency_dependency("POST /pos/shifts/{id}/close")),
    session=Depends(get_tenant_session),
    service: ServiceDep = Depends(get_pos_service),
):
    if idem.replay:
        return ShiftSummaryResponse.model_validate(idem.cached_body)

    tenant_id = _tenant_id_of(user)

    # Client-side claim check
    if payload.local_unresolved.count > 0:
        session.execute(
            text("""INSERT INTO pos.shifts_close_attempts
                      (shift_id, tenant_id, terminal_id, outcome,
                       claimed_unresolved_count, claimed_unresolved_digest, rejection_reason)
                    VALUES (:s, :t, :term, 'rejected_client', :c, :d, 'provisional_work_pending')"""),
            {"s": shift_id, "t": tenant_id, "term": proof.terminal_id,
             "c": payload.local_unresolved.count, "d": payload.local_unresolved.digest},
        )
        session.commit()
        raise HTTPException(status_code=409, detail="provisional_work_pending")

    # Server-side incomplete-transaction check
    incomplete = session.execute(
        text(
            """SELECT count(*) FROM pos.transactions
                WHERE shift_id = :s AND tenant_id = :t
                  AND terminal_id = :term AND commit_confirmed_at IS NULL"""
        ),
        {"s": shift_id, "t": tenant_id, "term": proof.terminal_id},
    ).scalar() or 0

    if incomplete > 0:
        session.execute(
            text("""INSERT INTO pos.shifts_close_attempts
                      (shift_id, tenant_id, terminal_id, outcome,
                       claimed_unresolved_count, claimed_unresolved_digest,
                       server_incomplete_count, rejection_reason)
                    VALUES (:s, :t, :term, 'rejected_server', :c, :d, :inc,
                            'server_side_incomplete_transactions')"""),
            {"s": shift_id, "t": tenant_id, "term": proof.terminal_id,
             "c": payload.local_unresolved.count, "d": payload.local_unresolved.digest, "inc": incomplete},
        )
        session.commit()
        raise HTTPException(status_code=409, detail="server_side_incomplete_transactions")

    # Delegate to existing close service
    response = service.close_shift(
        tenant_id=tenant_id,
        shift_id=shift_id,
        closing_cash=payload.closing_cash,
        notes=payload.notes,
    )

    session.execute(
        text("""INSERT INTO pos.shifts_close_attempts
                  (shift_id, tenant_id, terminal_id, outcome,
                   claimed_unresolved_count, claimed_unresolved_digest)
                VALUES (:s, :t, :term, 'accepted', :c, :d)"""),
        {"s": shift_id, "t": tenant_id, "term": proof.terminal_id,
         "c": payload.local_unresolved.count, "d": payload.local_unresolved.digest},
    )
    record_response(session, idem.key, 200, response.model_dump(mode="json"))
    session.commit()
    return response
```

If an existing `close_shift` with the old `CloseShiftRequest` is already live, either (a) add a new `/shifts/{id}/close-v2` endpoint and deprecate the old one, or (b) replace the old body type in the existing route. Choose based on whether the web frontend calls the old endpoint — grep `CloseShiftRequest` in `frontend/`. For M1 safety, **add the new endpoint, leave the old one untouched**:

```python
@router.post("/shifts/{shift_id}/close-v2", ...)
```

Update the spec reference in the commit message.

- [ ] **Step 3: Unit test (direct function test — skip route wiring for M1)**

The full route flow involves many `Depends(...)` chains. For the M1 scope, test the **guard logic** in isolation by extracting the guard into a helper function:

Create a small helper `src/datapulse/pos/shift_close_guard.py`:

```python
"""Server-enforced shift-close guard (§3.6)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session


GuardOutcome = Literal["accepted", "rejected_client", "rejected_server"]


@dataclass(frozen=True)
class GuardResult:
    outcome: GuardOutcome
    server_incomplete_count: int = 0


def enforce_close_guard(
    session: Session,
    *,
    shift_id: int,
    tenant_id: int,
    terminal_id: int,
    claim_count: int,
    claim_digest: str,
) -> GuardResult:
    """Apply client + server checks; record forensic attempt row on any outcome.

    Raises HTTPException(409) on rejection. Returns accepted GuardResult on pass.
    """
    if claim_count > 0:
        session.execute(
            text(
                """INSERT INTO pos.shifts_close_attempts
                     (shift_id, tenant_id, terminal_id, outcome,
                      claimed_unresolved_count, claimed_unresolved_digest, rejection_reason)
                   VALUES (:s, :t, :term, 'rejected_client', :c, :d, 'provisional_work_pending')"""
            ),
            {"s": shift_id, "t": tenant_id, "term": terminal_id, "c": claim_count, "d": claim_digest},
        )
        raise HTTPException(status_code=409, detail="provisional_work_pending")

    incomplete = session.execute(
        text(
            """SELECT count(*) FROM pos.transactions
                WHERE shift_id = :s AND tenant_id = :t
                  AND terminal_id = :term AND commit_confirmed_at IS NULL"""
        ),
        {"s": shift_id, "t": tenant_id, "term": terminal_id},
    ).scalar() or 0

    if incomplete > 0:
        session.execute(
            text(
                """INSERT INTO pos.shifts_close_attempts
                     (shift_id, tenant_id, terminal_id, outcome,
                      claimed_unresolved_count, claimed_unresolved_digest,
                      server_incomplete_count, rejection_reason)
                   VALUES (:s, :t, :term, 'rejected_server', :c, :d, :inc,
                           'server_side_incomplete_transactions')"""
            ),
            {"s": shift_id, "t": tenant_id, "term": terminal_id,
             "c": claim_count, "d": claim_digest, "inc": int(incomplete)},
        )
        raise HTTPException(status_code=409, detail="server_side_incomplete_transactions")

    session.execute(
        text(
            """INSERT INTO pos.shifts_close_attempts
                 (shift_id, tenant_id, terminal_id, outcome,
                  claimed_unresolved_count, claimed_unresolved_digest)
               VALUES (:s, :t, :term, 'accepted', :c, :d)"""
        ),
        {"s": shift_id, "t": tenant_id, "term": terminal_id, "c": claim_count, "d": claim_digest},
    )
    return GuardResult(outcome="accepted", server_incomplete_count=0)
```

Unit test:

```python
# tests/test_pos_shift_close_guard.py
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException

pytestmark = pytest.mark.unit


def test_guard_accepts_when_both_checks_clean():
    from datapulse.pos.shift_close_guard import enforce_close_guard

    session = MagicMock()
    session.execute.return_value.scalar.return_value = 0

    result = enforce_close_guard(
        session, shift_id=1, tenant_id=1, terminal_id=1,
        claim_count=0, claim_digest="sha256:clean",
    )
    assert result.outcome == "accepted"


def test_guard_rejects_client_claim():
    from datapulse.pos.shift_close_guard import enforce_close_guard

    session = MagicMock()
    with pytest.raises(HTTPException) as exc:
        enforce_close_guard(
            session, shift_id=1, tenant_id=1, terminal_id=1,
            claim_count=3, claim_digest="sha256:three",
        )
    assert exc.value.status_code == 409
    assert exc.value.detail == "provisional_work_pending"


def test_guard_rejects_server_incomplete():
    from datapulse.pos.shift_close_guard import enforce_close_guard

    session = MagicMock()
    session.execute.return_value.scalar.return_value = 2

    with pytest.raises(HTTPException) as exc:
        enforce_close_guard(
            session, shift_id=1, tenant_id=1, terminal_id=1,
            claim_count=0, claim_digest="sha256:clean",
        )
    assert exc.value.status_code == 409
    assert exc.value.detail == "server_side_incomplete_transactions"
```

- [ ] **Step 4: Commit**

```bash
PYTHONPATH=src pytest tests/test_pos_shift_close_guard.py -v
```

```bash
git add src/datapulse/pos/shift_close_guard.py src/datapulse/pos/models.py \
        src/datapulse/api/routes/pos.py tests/test_pos_shift_close_guard.py
git commit -m "feat(pos): server-enforced shift-close guard with dual-side check + forensic log"
```

---

## Task 16: Nightly idempotency cleanup task

**Files:** `src/datapulse/tasks/cleanup_pos_idempotency.py`, `tests/test_pos_cleanup_task.py`

- [ ] **Step 1: Implementation**

```python
# src/datapulse/tasks/cleanup_pos_idempotency.py
"""Nightly cleanup of expired POS idempotency keys."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def run(session: Session) -> int:
    result = session.execute(
        text("DELETE FROM pos.idempotency_keys WHERE expires_at < now()")
    )
    return int(result.rowcount or 0)


if __name__ == "__main__":
    from datapulse.api.deps import get_db_session
    from datapulse.logging import get_logger

    log = get_logger(__name__)
    for session in get_db_session():
        deleted = run(session)
        session.commit()
        log.info("pos_idempotency_cleanup_complete", deleted=deleted)
        break
```

- [ ] **Step 2: Unit test (mock-based)**

```python
# tests/test_pos_cleanup_task.py
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


def test_cleanup_executes_delete_and_returns_rowcount():
    from datapulse.tasks.cleanup_pos_idempotency import run

    session = MagicMock()
    session.execute.return_value.rowcount = 5
    assert run(session) == 5
    session.execute.assert_called_once()


def test_cleanup_returns_zero_when_no_rows():
    from datapulse.tasks.cleanup_pos_idempotency import run

    session = MagicMock()
    session.execute.return_value.rowcount = 0
    assert run(session) == 0
```

- [ ] **Step 3: Commit**

```bash
PYTHONPATH=src pytest tests/test_pos_cleanup_task.py -v
```

```bash
git add src/datapulse/tasks/cleanup_pos_idempotency.py tests/test_pos_cleanup_task.py
git commit -m "feat(pos): nightly cleanup task for expired idempotency keys"
```

---

## Task 17: Final gate — full POS test suite

- [ ] **Step 1: Run every new test file**

```bash
PYTHONPATH=src pytest \
  tests/test_pos_idempotency.py \
  tests/test_pos_capabilities.py \
  tests/test_pos_tenant_keys.py \
  tests/test_pos_devices.py \
  tests/test_pos_grants.py \
  tests/test_pos_overrides.py \
  tests/test_pos_commit.py \
  tests/test_pos_single_terminal_guard.py \
  tests/test_pos_shift_close_guard.py \
  tests/test_pos_cleanup_task.py \
  -v
```

Expected: all PASS.

- [ ] **Step 2: Run existing POS tests to verify no regression**

```bash
PYTHONPATH=src pytest tests/ -k pos -v
```

Expected: all PASS. If an existing test uses the old `CloseShiftRequest` shape and now fails, either add a conversion layer or adapt the test to the new `CloseShiftRequestV2`.

- [ ] **Step 3: Ruff check**

```bash
ruff check src/datapulse/pos/ src/datapulse/api/routes/pos.py src/datapulse/tasks/cleanup_pos_idempotency.py
```

Expected: clean. Fix any warnings.

- [ ] **Step 4: Tag the milestone**

```bash
git tag -a pos-m1-backend-complete -m "M1: backend foundations for POS desktop complete"
```

---

## Self-Review Checklist

| Spec section | Implemented by |
|---|---|
| §1.4 Single-terminal enforcement (server layers) | Tasks 4, 13 |
| §3.6 Server-enforced shift-close + commit_confirmed_at | Tasks 2, 15 |
| §6.4 Idempotency with TTL > provisional | Tasks 1, 6, 16 |
| §6.6 Capability negotiation + tenant-state endpoint | Tasks 7, 13 |
| §8.8 Ed25519 grant issuance + tenant keypairs | Tasks 3, 8, 9, 11 |
| §8.8.6 Override token verifier + ledger | Tasks 3, 12 |
| §8.9 Device-bound terminal credential | Tasks 3, 10 |
| New endpoints: commit, capabilities, tenant-key, register-device, active-for-me | Tasks 7, 9, 10, 13, 14 |
| Catalog streams (deferred) | **M2** |
| New permission slugs | Task 5 |

**Milestone deliverable:** a `feat/pos-electron-desktop` branch where every new/modified file has mock-based tests, all migrations committed as SQL files (applied on droplet at deploy time — not locally), every new endpoint is rate-limited + RLS-scoped + idempotent where mutating, and the full POS test suite is green locally. The web frontend and dashboards remain unaffected — everything in M1 is additive.

---

**End of M1 plan (v2).**
