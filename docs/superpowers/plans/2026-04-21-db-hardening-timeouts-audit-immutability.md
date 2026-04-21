# DB Hardening — Role Timeouts + Audit Log Immutability (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one idempotent SQL migration that (a) sets statement/idle/lock timeouts as role defaults on `datapulse` and `datapulse_reader`, and (b) makes `public.audit_log` append-only via a trigger that fires against the owner role. Add two integration test files that verify both behaviours against a real Postgres.

**Architecture:** DB-level invariants only — no application code changes. The migration follows the idempotent `DO $$ ... EXCEPTION ... END $$` pattern used by siblings `002`, `014`, `030c`, `037`, `038`. Tests follow the `test_rls_db_integration.py` pattern: `pytestmark = pytest.mark.integration`, socket-based `requires_real_db` skip, module-scoped psycopg2 fixture. Migration is auto-applied by `scripts/prestart.sh` on container start.

**Tech Stack:** PostgreSQL 16, `psql`, `psycopg2` (in tests), `pytest`, SQLAlchemy (for the reader-role engine fixture).

**Spec:** `docs/superpowers/specs/2026-04-21-db-hardening-timeouts-audit-immutability-design.md`

---

## File Structure

| Path | Action | Responsibility |
|------|--------|----------------|
| `migrations/094_harden_db_roles_and_audit.sql` | Create | Role-level timeout defaults + audit_log append-only trigger + schema_migrations row |
| `tests/test_audit_log_immutability.py` | Create | Verify INSERT works, UPDATE/DELETE blocked for owner and reader, trigger fires |
| `tests/test_db_role_timeouts.py` | Create | Verify role-level `statement_timeout`, `idle_in_transaction_session_timeout`, `lock_timeout` and that `SET LOCAL` still overrides |

Nothing else changes. `deps.py` remains as-is.

---

## Preconditions

- Local Docker stack running (`docker compose up -d postgres api`) OR `DATABASE_URL` pointing at a reachable Postgres 16.
- `DB_READER_PASSWORD` env var set (exported or in `.env`). The migration needs it to confirm the reader role exists; tests need it to build the reader connection string.
- Migrations `002` and `014` have already applied (standard). `tests/test_rls_db_integration.py` passes today (smoke confirmation that the DB is in good shape).

---

## Task 1: Scaffold the two failing test files (RED baseline)

The migration hasn't been written yet. The tests we write here SHOULD fail today because:
- No trigger on `audit_log` exists → UPDATE/DELETE succeed instead of raising.
- Roles have `statement_timeout = 0` (unlimited) instead of the new defaults.

This is the RED state we want before writing the migration.

**Files:**
- Create: `tests/test_audit_log_immutability.py`
- Create: `tests/test_db_role_timeouts.py`

- [ ] **Step 1.1: Write `tests/test_audit_log_immutability.py`**

```python
"""DB-level audit_log immutability tests.

Verifies that the append-only trigger installed by migration 094 blocks
UPDATE and DELETE on public.audit_log for every role (including the
table owner ``datapulse``), while INSERT continues to work.

Runs against a real Postgres. Skipped when one is not reachable on
localhost:5432 — same pattern as test_rls_db_integration.py.
"""

from __future__ import annotations

import os
import socket

import pytest

pytestmark = pytest.mark.integration


def _db_is_reachable() -> bool:
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url or ("localhost" not in db_url and "127.0.0.1" not in db_url):
        return False
    try:
        with socket.create_connection(("127.0.0.1", 5432), timeout=1):
            return True
    except OSError:
        return False


requires_real_db = pytest.mark.skipif(
    not _db_is_reachable(),
    reason="Real PostgreSQL at localhost:5432 not reachable.",
)


def _reader_dsn() -> str:
    """Construct a reader-role DSN from DATABASE_URL + DB_READER_PASSWORD."""
    from urllib.parse import urlparse, urlunparse

    owner = urlparse(os.environ["DATABASE_URL"])
    reader_netloc = f"datapulse_reader:{os.environ['DB_READER_PASSWORD']}@{owner.hostname}:{owner.port or 5432}"
    return urlunparse(owner._replace(netloc=reader_netloc))


@pytest.fixture(scope="module")
def owner_conn():
    """Raw psycopg2 connection as the ``datapulse`` owner role."""
    psycopg2 = pytest.importorskip("psycopg2")
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.autocommit = False
    yield conn
    conn.rollback()
    conn.close()


@pytest.fixture(scope="module")
def reader_conn():
    """Raw psycopg2 connection as the ``datapulse_reader`` read-only role."""
    psycopg2 = pytest.importorskip("psycopg2")
    conn = psycopg2.connect(_reader_dsn())
    conn.autocommit = False
    yield conn
    conn.rollback()
    conn.close()


def _insert_audit_row(conn) -> int:
    """Insert one audit_log row and return its id. Caller must rollback."""
    with conn.cursor() as cur:
        cur.execute("BEGIN")
        cur.execute("SET LOCAL app.tenant_id = '1'")
        cur.execute(
            """
            INSERT INTO public.audit_log
                (tenant_id, action, endpoint, method, response_status)
            VALUES (1, 'test.immutable', '/test', 'GET', 200)
            RETURNING id
            """
        )
        return cur.fetchone()[0]


class TestAuditLogImmutability:
    @requires_real_db
    def test_insert_still_works(self, owner_conn) -> None:
        """INSERT must continue to succeed — trigger is UPDATE/DELETE only."""
        try:
            new_id = _insert_audit_row(owner_conn)
            assert new_id > 0
        finally:
            owner_conn.rollback()

    @requires_real_db
    def test_update_blocked_for_owner(self, owner_conn) -> None:
        """UPDATE as the ``datapulse`` owner role must raise insufficient_privilege."""
        psycopg2 = pytest.importorskip("psycopg2")
        try:
            new_id = _insert_audit_row(owner_conn)
            with owner_conn.cursor() as cur:
                with pytest.raises(psycopg2.errors.InsufficientPrivilege):
                    cur.execute(
                        "UPDATE public.audit_log SET action = 'tampered' WHERE id = %s",
                        (new_id,),
                    )
        finally:
            owner_conn.rollback()

    @requires_real_db
    def test_delete_blocked_for_owner(self, owner_conn) -> None:
        """DELETE as the ``datapulse`` owner role must raise insufficient_privilege."""
        psycopg2 = pytest.importorskip("psycopg2")
        try:
            new_id = _insert_audit_row(owner_conn)
            with owner_conn.cursor() as cur:
                with pytest.raises(psycopg2.errors.InsufficientPrivilege):
                    cur.execute(
                        "DELETE FROM public.audit_log WHERE id = %s",
                        (new_id,),
                    )
        finally:
            owner_conn.rollback()

    @requires_real_db
    def test_trigger_message_mentions_operation(self, owner_conn) -> None:
        """Trigger error message should name the blocked TG_OP for debuggability."""
        psycopg2 = pytest.importorskip("psycopg2")
        try:
            new_id = _insert_audit_row(owner_conn)
            with owner_conn.cursor() as cur:
                try:
                    cur.execute(
                        "UPDATE public.audit_log SET action = 'x' WHERE id = %s",
                        (new_id,),
                    )
                    pytest.fail("UPDATE should have raised InsufficientPrivilege")
                except psycopg2.errors.InsufficientPrivilege as e:
                    msg = str(e).lower()
                    assert "audit_log" in msg
                    assert "append-only" in msg or "update" in msg
        finally:
            owner_conn.rollback()
```

- [ ] **Step 1.2: Write `tests/test_db_role_timeouts.py`**

```python
"""DB-level role timeout tests.

Verifies that migration 094 set the expected statement/idle/lock timeouts
as role defaults on ``datapulse`` and ``datapulse_reader``, and that
``SET LOCAL`` in a transaction still overrides the role default.

Runs against a real Postgres. Skipped when one is not reachable.
"""

from __future__ import annotations

import os
import socket

import pytest

pytestmark = pytest.mark.integration


def _db_is_reachable() -> bool:
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url or ("localhost" not in db_url and "127.0.0.1" not in db_url):
        return False
    try:
        with socket.create_connection(("127.0.0.1", 5432), timeout=1):
            return True
    except OSError:
        return False


requires_real_db = pytest.mark.skipif(
    not _db_is_reachable(),
    reason="Real PostgreSQL at localhost:5432 not reachable.",
)


def _reader_dsn() -> str:
    from urllib.parse import urlparse, urlunparse

    owner = urlparse(os.environ["DATABASE_URL"])
    reader_netloc = f"datapulse_reader:{os.environ['DB_READER_PASSWORD']}@{owner.hostname}:{owner.port or 5432}"
    return urlunparse(owner._replace(netloc=reader_netloc))


@pytest.fixture
def owner_conn():
    """Fresh connection per test — role defaults only apply to new sessions."""
    psycopg2 = pytest.importorskip("psycopg2")
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.autocommit = True  # we only SHOW / SET LOCAL
    yield conn
    conn.close()


@pytest.fixture
def reader_conn():
    psycopg2 = pytest.importorskip("psycopg2")
    conn = psycopg2.connect(_reader_dsn())
    conn.autocommit = True
    yield conn
    conn.close()


def _show(conn, name: str) -> str:
    with conn.cursor() as cur:
        cur.execute(f"SHOW {name}")
        return cur.fetchone()[0]


class TestReaderRoleTimeouts:
    @requires_real_db
    def test_reader_statement_timeout_default(self, reader_conn) -> None:
        assert _show(reader_conn, "statement_timeout") == "15s"

    @requires_real_db
    def test_reader_idle_in_transaction_timeout_default(self, reader_conn) -> None:
        assert _show(reader_conn, "idle_in_transaction_session_timeout") == "30s"

    @requires_real_db
    def test_reader_lock_timeout_default(self, reader_conn) -> None:
        assert _show(reader_conn, "lock_timeout") == "5s"


class TestAppRoleTimeouts:
    @requires_real_db
    def test_app_statement_timeout_default(self, owner_conn) -> None:
        assert _show(owner_conn, "statement_timeout") == "2min"

    @requires_real_db
    def test_app_idle_in_transaction_timeout_default(self, owner_conn) -> None:
        assert _show(owner_conn, "idle_in_transaction_session_timeout") == "5min"

    @requires_real_db
    def test_app_lock_timeout_default(self, owner_conn) -> None:
        assert _show(owner_conn, "lock_timeout") == "10s"


class TestSessionLocalStillWins:
    @requires_real_db
    def test_set_local_overrides_role_default(self, owner_conn) -> None:
        """SET LOCAL inside a transaction must override the role-level default —
        proves deps.py SET LOCAL statement_timeout = '30s' still wins."""
        with owner_conn.cursor() as cur:
            cur.execute("BEGIN")
            cur.execute("SET LOCAL statement_timeout = '5s'")
            cur.execute("SHOW statement_timeout")
            value = cur.fetchone()[0]
            cur.execute("ROLLBACK")
        assert value == "5s"
```

- [ ] **Step 1.3: Run both test files to confirm the RED baseline**

Run:
```bash
DATABASE_URL="postgresql://datapulse:${POSTGRES_PASSWORD}@localhost:5432/datapulse" \
DB_READER_PASSWORD="${DB_READER_PASSWORD}" \
pytest -m integration tests/test_audit_log_immutability.py tests/test_db_role_timeouts.py -v
```

Expected:
- `test_insert_still_works` → PASS (INSERT has always worked; this is a sanity test)
- `test_update_blocked_for_owner` → **FAIL** (no trigger yet, UPDATE succeeds)
- `test_delete_blocked_for_owner` → **FAIL** (no trigger yet, DELETE succeeds)
- `test_trigger_message_mentions_operation` → **FAIL** (no trigger yet)
- All six timeout tests → **FAIL** (SHOW returns `"0"` which means unlimited, not `"15s"`/`"2min"`/etc.)
- `test_set_local_overrides_role_default` → PASS (SET LOCAL already works without the migration)

If any expected-FAIL test passes, something is off — stop and investigate before proceeding.

- [ ] **Step 1.4: Commit the failing tests**

```bash
git add tests/test_audit_log_immutability.py tests/test_db_role_timeouts.py
git commit -m "test(db): red baseline — audit_log immutability + role timeouts

Tests intentionally fail today. Migration 094 will turn them green."
```

---

## Task 2: Write migration 094 (GREEN step)

**Files:**
- Create: `migrations/094_harden_db_roles_and_audit.sql`

- [ ] **Step 2.1: Write the migration**

```sql
-- Migration 094: DB hardening — role timeouts + audit_log append-only trigger
--
-- Purpose:
--   1. Set statement/idle/lock timeouts as role defaults on datapulse and
--      datapulse_reader. This is a safety net — deps.py SET LOCAL overrides
--      these per-transaction — but catches any code that forgets to set them
--      or any direct psql connection.
--   2. Make public.audit_log append-only via a BEFORE UPDATE OR DELETE trigger.
--      REVOKE doesn't work because the owner role (datapulse) owns the table;
--      triggers fire regardless of ownership.
--
-- Run order: after 093_add_pos_device_fingerprint_v2.sql
-- Idempotent: safe to run multiple times (DO ... EXCEPTION guards, OR REPLACE,
-- DROP TRIGGER IF EXISTS, ON CONFLICT DO NOTHING).
-- Requires: migrations 002 (roles) and 014 (audit_log with RLS) applied.

BEGIN;

INSERT INTO public.schema_migrations (filename)
VALUES ('094_harden_db_roles_and_audit.sql')
ON CONFLICT (filename) DO NOTHING;

-- ============================================================
-- Section A — Role-level timeout defaults
-- ============================================================
-- These apply to NEW sessions. Existing sessions keep their current settings
-- until reconnect. deps.py SET LOCAL statement_timeout = '30s' still wins
-- inside an application transaction (tighter than 15s reader / 2min app).

DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'datapulse_reader') THEN
        ALTER ROLE datapulse_reader SET statement_timeout = '15s';
        ALTER ROLE datapulse_reader SET idle_in_transaction_session_timeout = '30s';
        ALTER ROLE datapulse_reader SET lock_timeout = '5s';
    ELSE
        RAISE NOTICE 'Role datapulse_reader not present — skipping reader timeouts';
    END IF;
END $$;

DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'datapulse') THEN
        ALTER ROLE datapulse SET statement_timeout = '2min';
        ALTER ROLE datapulse SET idle_in_transaction_session_timeout = '5min';
        ALTER ROLE datapulse SET lock_timeout = '10s';
    ELSE
        RAISE NOTICE 'Role datapulse not present — skipping app timeouts';
    END IF;
END $$;

-- ============================================================
-- Section B — audit_log append-only trigger
-- ============================================================
-- Triggers fire against all roles, including the table owner. This is the
-- canonical Postgres pattern for append-only enforcement — REVOKE UPDATE
-- on an owned table is a no-op. Bypass only via superuser + SET
-- session_replication_role = 'replica' (reserved for future retention jobs).

CREATE OR REPLACE FUNCTION public.audit_log_immutable()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only (% blocked)', TG_OP
        USING ERRCODE = 'insufficient_privilege',
              HINT    = 'Use SET session_replication_role = ''replica'' '
                        'from a superuser retention job to bypass.';
END;
$fn$;

DROP TRIGGER IF EXISTS tg_audit_log_immutable ON public.audit_log;
CREATE TRIGGER tg_audit_log_immutable
    BEFORE UPDATE OR DELETE ON public.audit_log
    FOR EACH ROW
    EXECUTE FUNCTION public.audit_log_immutable();

COMMENT ON TRIGGER tg_audit_log_immutable ON public.audit_log IS
    'Enforces append-only on audit_log. UPDATE/DELETE raise '
    'insufficient_privilege regardless of role, including the owner. '
    'Bypass via SET session_replication_role = ''replica'' (superuser only).';

COMMIT;
```

Notes on the values — Postgres normalises `'120s'` → `'2min'` on ALTER ROLE, so the test asserts `"2min"`, not `"120s"`. Same for `'300s'` → `'5min'`.

- [ ] **Step 2.2: Apply the migration to the dev DB**

Option A (clean — goes through prestart.sh like prod does):
```bash
docker compose restart api
docker compose logs api --tail 40 | grep -E "094_|Applying|ERROR"
```

Expected log line: `[prestart] Applying: 094_harden_db_roles_and_audit.sql`

Option B (fast — direct psql, for iterative work):
```bash
docker exec -i datapulse-db psql -U datapulse -d datapulse < migrations/094_harden_db_roles_and_audit.sql
```

Either way, verify:
```bash
docker exec -i datapulse-db psql -U datapulse -d datapulse -c \
  "SELECT filename FROM public.schema_migrations WHERE filename = '094_harden_db_roles_and_audit.sql'"
```
Expected: one row returned.

- [ ] **Step 2.3: Re-run the test suite — expect GREEN**

Run:
```bash
DATABASE_URL="postgresql://datapulse:${POSTGRES_PASSWORD}@localhost:5432/datapulse" \
DB_READER_PASSWORD="${DB_READER_PASSWORD}" \
pytest -m integration tests/test_audit_log_immutability.py tests/test_db_role_timeouts.py -v
```

Expected: **all 11 tests PASS.**

If any fail, read the error carefully:
- `InsufficientPrivilege` not raised → trigger not installed correctly; re-check `\d+ public.audit_log` for trigger presence.
- Timeout `SHOW` returns `"0"` → role default didn't apply; role-level settings only take effect on NEW sessions. Close existing psql/connection-pool sessions and reopen.
- Role `datapulse_reader` password mismatch → verify `DB_READER_PASSWORD` env matches the one used at role creation in migration 002.

- [ ] **Step 2.4: Commit the migration**

```bash
git add migrations/094_harden_db_roles_and_audit.sql
git commit -m "feat(db): migration 094 — role timeouts + audit_log append-only trigger

Sets statement/idle/lock timeouts as role defaults on datapulse and
datapulse_reader as a safety net for deps.py SET LOCAL. Adds a BEFORE
UPDATE OR DELETE trigger on public.audit_log that raises
insufficient_privilege — fires against the owner role too, since REVOKE
on an owned table is a no-op in Postgres.

Turns tests from previous commit green."
```

---

## Task 3: Idempotency check

The migration must be safe to run twice.

- [ ] **Step 3.1: Re-apply the migration — should be a no-op**

```bash
docker exec -i datapulse-db psql -U datapulse -d datapulse < migrations/094_harden_db_roles_and_audit.sql
```

Expected: `COMMIT` with no errors. `CREATE OR REPLACE FUNCTION`, `DROP TRIGGER IF EXISTS`, `ON CONFLICT DO NOTHING` all handle re-runs.

- [ ] **Step 3.2: Re-run the tests — still GREEN**

```bash
DATABASE_URL="postgresql://datapulse:${POSTGRES_PASSWORD}@localhost:5432/datapulse" \
DB_READER_PASSWORD="${DB_READER_PASSWORD}" \
pytest -m integration tests/test_audit_log_immutability.py tests/test_db_role_timeouts.py -v
```

Expected: all 11 pass again.

---

## Task 4: Regression sanity — no app code modifies audit_log

The spec requires: no application code path issues UPDATE/DELETE against `public.audit_log`. If there is one, the migration will break prod. Verify before merge.

- [ ] **Step 4.1: Grep for UPDATE/DELETE audit_log in application code**

Run:
```bash
grep -rnE "UPDATE[[:space:]]+(public\.)?audit_log|DELETE[[:space:]]+FROM[[:space:]]+(public\.)?audit_log" src/ --include="*.py"
```

Expected output: **empty**. The audit service only inserts rows.

If any match surfaces in `src/`: stop, investigate, decide whether to keep the trigger or restructure that code path. Paste grep output in the PR description regardless (proves the check was done).

- [ ] **Step 4.2: Grep test code as a secondary check**

```bash
grep -rnE "UPDATE[[:space:]]+(public\.)?audit_log|DELETE[[:space:]]+FROM[[:space:]]+(public\.)?audit_log" tests/ --include="*.py"
```

Expected: only the new `test_update_blocked_for_owner` / `test_delete_blocked_for_owner` test code in `test_audit_log_immutability.py`.

---

## Task 5: Full test suite regression check

Nothing outside `audit_log` and role settings should have changed, but verify.

- [ ] **Step 5.1: Run the fast unit suite (same as CI gate)**

```bash
ruff format --check src/ tests/
ruff check src/ tests/
pytest -m "not integration" -x -q --timeout=30
```

Expected: all green, no new lint warnings.

- [ ] **Step 5.2: Run the integration suite (subset, scoped to DB-level tests)**

```bash
DATABASE_URL="postgresql://datapulse:${POSTGRES_PASSWORD}@localhost:5432/datapulse" \
DB_READER_PASSWORD="${DB_READER_PASSWORD}" \
pytest -m integration tests/test_rls_db_integration.py tests/test_audit_log_immutability.py tests/test_db_role_timeouts.py -v
```

Expected: `test_rls_db_integration.py` still passes (we didn't touch RLS). New tests all green.

---

## Task 6: Manual verification — single source of truth

Per the spec's success criteria, confirm end-to-end from a plain `psql` shell.

- [ ] **Step 6.1: Verify the trigger is installed**

```bash
docker exec -i datapulse-db psql -U datapulse -d datapulse -c "\d+ public.audit_log" | grep -A2 Triggers
```

Expected: `tg_audit_log_immutable BEFORE UPDATE OR DELETE ON public.audit_log FOR EACH ROW EXECUTE FUNCTION public.audit_log_immutable()`

- [ ] **Step 6.2: Verify the role defaults are persisted**

```bash
docker exec -i datapulse-db psql -U datapulse -d datapulse -c \
  "SELECT rolname, rolconfig FROM pg_roles WHERE rolname IN ('datapulse', 'datapulse_reader')"
```

Expected: `rolconfig` for each role contains `statement_timeout=...`, `idle_in_transaction_session_timeout=...`, `lock_timeout=...` entries.

- [ ] **Step 6.3: Hand-roll an UPDATE attempt**

```bash
docker exec -i datapulse-db psql -U datapulse -d datapulse -c \
  "UPDATE public.audit_log SET action = 'hand-test' WHERE id = (SELECT id FROM public.audit_log LIMIT 1)"
```

Expected: `ERROR: audit_log is append-only (UPDATE blocked)` (or `no rows` if the table is empty — in that case insert a row first).

---

## Task 7: Final commit + PR prep

- [ ] **Step 7.1: Stage everything and run final CI gate locally**

```bash
ruff format --check src/ tests/
ruff check src/ tests/
pytest -m "not integration" -x -q --timeout=30
```

Expected: all green.

- [ ] **Step 7.2: Verify git status is clean and changes are expected**

```bash
git status
git log --oneline main..HEAD
```

Expected commits (in order):
1. `docs(spec): DB hardening — role timeouts + audit log immutability design` (already present)
2. `test(db): red baseline — audit_log immutability + role timeouts`
3. `feat(db): migration 094 — role timeouts + audit_log append-only trigger`

- [ ] **Step 7.3: Push and open a PR**

```bash
git push -u origin claude/optimistic-germain-ac3976
gh pr create --title "feat(db): fortification #1 — role timeouts + audit_log immutability" --body "$(cat <<'EOF'
## Summary
- Adds migration 094: role-level `statement_timeout` / `idle_in_transaction_session_timeout` / `lock_timeout` defaults on `datapulse` (2min/5min/10s) and `datapulse_reader` (15s/30s/5s).
- Adds a BEFORE UPDATE OR DELETE trigger on `public.audit_log` that raises `insufficient_privilege` — enforces append-only against the owner role too (REVOKE cannot do this on an owned table in Postgres).
- No application code changes. `deps.py` SET LOCAL still wins per-transaction.

## Spec
`docs/superpowers/specs/2026-04-21-db-hardening-timeouts-audit-immutability-design.md`

## Test plan
- [x] `pytest -m integration tests/test_audit_log_immutability.py tests/test_db_role_timeouts.py -v` — all green
- [x] `pytest -m "not integration" -x -q` — full unit suite green
- [x] Migration is idempotent (verified by re-running)
- [x] Grep for `UPDATE audit_log` / `DELETE FROM audit_log` in `src/` — empty
- [x] Manual psql verification — trigger fires, role defaults persist

## Follow-ups
- Retention runbook: `docs/runbooks/audit-log-retention.md` when first needed.
- Apply same pattern to `pos_void_log`, `pos_override_consumptions`, `pos_shifts_close_attempts` (separate PR each — different retention contracts).
- Observability alert on `insufficient_privilege` from `audit_log` (likely bug/attack signal).
EOF
)"
```

---

## Self-Review — spec coverage

| Spec section | Covered by |
|--------------|------------|
| §3.1 Section A (role timeouts) | Task 2 Step 2.1, Task 1 Step 1.2 |
| §3.1 Section B (immutability trigger) | Task 2 Step 2.1, Task 1 Step 1.1 |
| §3.1 Section C (idempotency + schema_migrations row) | Task 2 Step 2.1 (DO blocks + ON CONFLICT), Task 3 |
| §3.2 test_audit_log_immutability.py | Task 1 Step 1.1 — 4 tests (spec called out 5; `test_retention_bypass_pattern` deferred as out-of-scope — see deferral note below) |
| §3.2 test_db_role_timeouts.py | Task 1 Step 1.2 — 7 tests |
| §3.3 No app code changes | Confirmed by Task 4 grep |
| §6 Success criteria | Tasks 3, 4, 5, 6 |
| §7 Dependencies | Preconditions section |

**Deferred:** `test_retention_bypass_pattern` from spec §3.2. Reason: requires a superuser-level connection to set `session_replication_role = 'replica'`, which isn't part of our standard local stack and would add a skip-guarded test that documents a pattern we haven't built yet. Captured as a follow-up in Task 7 PR body ("Retention runbook") — when the runbook is written, a matching test can be added alongside it. This deferral was flagged as acceptable in the spec's §2 Non-goals ("Retention/archival flow").

**Placeholder scan:** no TBD / TODO / "implement later" in any step. Every code/command block is runnable as-is (after `DATABASE_URL` + `DB_READER_PASSWORD` are set in the shell).

**Type/name consistency:**
- Function: `public.audit_log_immutable()` — used in Task 2 Step 2.1 and verified in Task 6 Step 6.1.
- Trigger: `tg_audit_log_immutable` — same in both places.
- Error code: `insufficient_privilege` (42501) — same in migration and tests.
- Timeout values: 15s/30s/5s (reader), 2min/5min/10s (app) — same in migration and test assertions.
