# DB Hardening — Role Timeouts + Audit Log Immutability

- **Date:** 2026-04-21
- **Status:** Draft — awaiting user review
- **Scope:** Single migration + two test files. One PR.
- **Context:** Residual gap from the Fortification Ordering A (items #1 + #2). Both are
  DB-level, migration-only, and share the same concern: enforce invariants at the
  database so application-level discipline cannot be the only line of defense.

---

## 1. Problem

Two gaps remain after H1–H5 + T1–T4:

### 1.1 Timeouts are per-session only, not role-default

`src/datapulse/api/deps.py` sets `SET LOCAL statement_timeout = '30s'` inside every
`get_plain_session`, `get_db_session`, and `get_tenant_session` generator. This works
for normal API traffic, but:

- If a future session generator is added without this `SET LOCAL`, the session has
  unbounded timeout.
- If a script, cron job, or direct `psql` connects using the `datapulse` or
  `datapulse_reader` role, no timeout applies.
- `idle_in_transaction_session_timeout` is not set anywhere — a connection can hold
  a transaction open indefinitely, pinning a pool slot.
- `lock_timeout` is not set — a migration that collides with a long-running query
  can block indefinitely.

### 1.2 Audit log is not append-only at the DB level

`migrations/014_add_audit_log_tenant_user.sql` grants:

```sql
CREATE POLICY owner_all ON public.audit_log
    FOR ALL TO datapulse
    USING (true) WITH CHECK (true);
```

`FOR ALL` permits `INSERT, UPDATE, DELETE`. The app role owns the table, so
`REVOKE UPDATE ON public.audit_log FROM datapulse` would be a no-op (owners always
retain privileges on their own objects in PostgreSQL). An application bug, a
compromised credential, or a malicious insider with DB access can rewrite or erase
audit history.

This is the forensic floor for every security investigation — losing it is
catastrophic.

---

## 2. Non-goals

Deliberately out of scope for this PR:

- **Retention / archival flow.** No rows old enough to matter. When needed, add a
  separate superuser-only job that uses `SET session_replication_role = 'replica'`
  to bypass the trigger. Design that in a follow-up spec.
- **Hash-chained / signed audit entries.** Future compliance work (SOC2, ISO
  27001); not this PR.
- **Extending the trigger to other append-only-ish tables** (`pos_void_log`,
  `pos_override_consumptions`, `pos_shifts_close_attempts`). Same pattern applies
  but each has its own retention semantics — follow-up PR per table.
- **Connection-pool-level timeouts** (pgbouncer `server_idle_timeout` etc). T1
  already tuned SQLAlchemy pool (5/10/10s).

---

## 3. Design

### 3.1 Migration `094_harden_db_roles_and_audit.sql`

Single idempotent migration, three logical sections:

**Section A — Role-level timeout defaults** (safety net if session-level
`SET LOCAL` is ever missing):

```sql
-- Reader role (API reads, tight bounds)
ALTER ROLE datapulse_reader SET statement_timeout = '15s';
ALTER ROLE datapulse_reader SET idle_in_transaction_session_timeout = '30s';
ALTER ROLE datapulse_reader SET lock_timeout = '5s';

-- App role (pipeline + dbt + migrations, looser bounds)
ALTER ROLE datapulse SET statement_timeout = '120s';
ALTER ROLE datapulse SET idle_in_transaction_session_timeout = '5min';
ALTER ROLE datapulse SET lock_timeout = '10s';
```

**Rationale for specific values:**
- Reader 15s: API reads currently p95 well under 2s; 15s is a generous ceiling.
- App 120s: dbt models and pipeline executors run up to ~90s in prod.
- `idle_in_transaction` reader 30s / app 5min: reader transactions are tiny;
  app may legitimately hold a transaction open during multi-stage pipeline work.
- `lock_timeout` reader 5s / app 10s: migrations (app role) may need to acquire
  ACCESS EXCLUSIVE; failing fast is better than deadlocking prod.

**Session-level `SET LOCAL statement_timeout = '30s'` in deps.py still wins** —
it overrides the role default per-transaction, and the role default is the safety
net.

**Section B — Audit log append-only trigger:**

```sql
CREATE OR REPLACE FUNCTION public.audit_log_immutable()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only (% blocked)', TG_OP
        USING ERRCODE = 'insufficient_privilege',
              HINT    = 'Use SET session_replication_role = ''replica'' '
                        'from a superuser-only retention job to bypass.';
END;
$fn$;

DROP TRIGGER IF EXISTS tg_audit_log_immutable ON public.audit_log;
CREATE TRIGGER tg_audit_log_immutable
    BEFORE UPDATE OR DELETE ON public.audit_log
    FOR EACH ROW
    EXECUTE FUNCTION public.audit_log_immutable();
```

**Why trigger, not REVOKE:** Postgres table owners cannot be stripped of
`UPDATE/DELETE` via `REVOKE` — ownership carries inherent privileges. Triggers
fire against all roles (including the owner), except when
`session_replication_role = 'replica'`, which is reserved for our future
retention job run by a superuser-only credential (never the app).

**Why BEFORE, not INSTEAD OF:** `INSTEAD OF` triggers only apply to views.
`BEFORE UPDATE OR DELETE FOR EACH ROW` with `RAISE EXCEPTION` is the canonical
Postgres append-only pattern.

**ERRCODE `insufficient_privilege` (42501):** maps cleanly to the existing
FastAPI exception handler path and to PostgreSQL client expectations.

**Section C — Idempotency + schema_migrations:**

- Guard role alterations with `DO $$ BEGIN ... EXCEPTION ... END $$` to skip
  if the role is missing in dev environments.
- `INSERT INTO public.schema_migrations (filename) VALUES ('094_...')
  ON CONFLICT DO NOTHING;` — same pattern as sibling migrations.
- `BEGIN; ... COMMIT;` wraps the whole file.

### 3.2 Tests

**`tests/test_audit_log_immutability.py` (new):**

```python
@pytest.mark.integration
class TestAuditLogImmutability:
    def test_insert_still_works(self, engine): ...
        # INSERT a row as datapulse — succeeds.

    def test_update_blocked_for_owner(self, engine): ...
        # UPDATE as datapulse raises psycopg2.errors.InsufficientPrivilege.

    def test_delete_blocked_for_owner(self, engine): ...
        # DELETE as datapulse raises psycopg2.errors.InsufficientPrivilege.

    def test_update_blocked_for_reader(self, reader_engine): ...
        # Reader lacks grant anyway, but verify the trigger also fires
        # (defense-in-depth assertion).

    def test_retention_bypass_pattern(self, superuser_engine): ...
        # With session_replication_role='replica', DELETE succeeds.
        # Documents the bypass contract — if this test breaks, retention
        # runbook must change.
```

Tests skip-guarded with `@pytest.mark.skipif(not DB_AVAILABLE)` matching the
pattern in `test_rls_db_integration.py`.

**`tests/test_db_role_timeouts.py` (new):**

```python
@pytest.mark.integration
class TestRoleTimeouts:
    def test_reader_statement_timeout_default(self, reader_engine): ...
        # SHOW statement_timeout -> '15s'

    def test_reader_idle_timeout_default(self, reader_engine): ...
        # SHOW idle_in_transaction_session_timeout -> '30s'

    def test_app_statement_timeout_default(self, engine): ...
        # SHOW statement_timeout -> '120s'

    def test_app_lock_timeout_default(self, engine): ...
        # SHOW lock_timeout -> '10s'

    def test_session_local_overrides_role_default(self, engine): ...
        # SET LOCAL statement_timeout = '5s' -> SHOW returns '5s'
        # Proves deps.py SET LOCAL still wins.
```

### 3.3 Application code — no changes

`deps.py` remains as-is. The `SET LOCAL statement_timeout = '30s'` is untouched
and still correct — tighter than the role default for API reads, which is the
right posture. The role defaults are a floor, not a ceiling.

---

## 4. Rollout

1. **Local:** run migration against dev DB, run new test files.
2. **Staging:** deploy, smoke-test `/health`, `/api/v1/analytics/summary`,
   one audit-log-emitting path.
3. **Prod:** deploy in a low-traffic window. Idempotent migration —
   re-runnable. Zero downtime (ALTER ROLE does not block active sessions;
   new sessions pick up defaults).

**Rollback:** migration `095_revert_094_hardening.sql` drops the trigger and
resets role defaults to `DEFAULT`. Kept handy but not expected to be needed —
changes are additive and reversible.

---

## 5. Risks + mitigations

| Risk | Mitigation |
|------|------------|
| App code that batch-updates `audit_log` silently fails in prod | Grep for `UPDATE audit_log` and `DELETE FROM audit_log` before merge — none expected, but verify. Include grep output in PR description. |
| Role timeout break a long-running dbt model | 120s ceiling is generous vs. current p95 ~30s. If a specific dbt model needs more, it sets `SET LOCAL` in its pre-hook. |
| `idle_in_transaction_session_timeout` breaks a slow test that holds a transaction | Tests explicitly override with `SET LOCAL` when needed. Existing tests reviewed; none currently hold transactions open > 30s. |
| Retention bypass pattern mis-remembered, someone tries plain DELETE | Trigger HINT message tells them exactly what to do. Runbook cross-references this spec. |

---

## 6. Success criteria

- [ ] Migration applies cleanly on fresh DB and on current prod snapshot.
- [ ] Migration is idempotent (re-running is a no-op).
- [ ] All new tests pass.
- [ ] Existing test suite (≥95% coverage gate) still passes.
- [ ] `grep -rn "UPDATE audit_log\|DELETE FROM audit_log" src/` returns no
  application code (only test/retention paths, if any).
- [ ] Manual verification: `psql` as `datapulse`, attempt
  `UPDATE public.audit_log SET action='x'` → raises 42501.
- [ ] Manual verification: `psql` as `datapulse_reader`, `SHOW statement_timeout`
  returns `15s`.

---

## 7. Dependencies on existing work

- Builds on `migrations/002_add_rls_and_roles.sql` (role creation).
- Builds on `migrations/014_add_audit_log_tenant_user.sql` (audit_log RLS).
- Coexists with `src/datapulse/api/deps.py` `SET LOCAL` (unchanged).
- Follows the same idempotent migration pattern as `030c`, `035`, `037`.

---

## 8. Open questions — resolved before writing plan

- **Q: Should we add the trigger to `pos_void_log` and
  `pos_override_consumptions` in this PR?**
  A: No — different retention contracts. Separate PR each. Tracked as
  follow-up in post-merge note.

- **Q: Should `datapulse_reader` get explicit REVOKE of UPDATE/DELETE on
  audit_log as belt-and-suspenders?**
  A: Reader already has no INSERT/UPDATE/DELETE grant (RLS allows SELECT only).
  Adding REVOKE is redundant. Trigger covers the owner case, which is the
  real threat model.

- **Q: Do we need a `statement_timeout` for the `dbt` runs specifically?**
  A: dbt runs as the `datapulse` role → picks up 120s role default. No
  separate role needed today. If prod dbt jobs ever exceed 120s, add
  `pre_hook = "SET LOCAL statement_timeout = '300s'"` to the specific model
  — do not raise the role default.

---

## 9. Follow-ups (out of this PR, tracked for later)

- Retention runbook: `docs/runbooks/audit-log-retention.md` when first needed.
- Same trigger pattern applied to `pos_void_log`, `pos_override_consumptions`,
  `pos_shifts_close_attempts`.
- Observability: alert on `insufficient_privilege` errors from the
  `audit_log` table — likely indicates a bug or attack attempt.
