# DataPulse — Full Project Audit

**Date:** 2026-04-21
**Branch:** `claude/project-audit-ZZwgn`
**Scope:** security, architecture, code quality, tests, database, DevOps, documentation
**Method:** six parallel read-only exploration agents (no code modified)

---

## Executive Summary

| Dimension       | Grade | Headline                                                              |
|-----------------|-------|-----------------------------------------------------------------------|
| DevOps / CI     | A-    | Strong hygiene; single CI gate; only the coverage threshold lies      |
| Code quality    | A-    | Ruff clean, 0 TODO markers, full Pydantic v2, strong type hints       |
| Database        | B     | Three duplicate migration numbers; mostly sound RLS                   |
| Architecture    | B     | Layer leaks concentrated in POS + RBAC + 14 routes                    |
| Tests           | B+    | 233 files / 3,364 tests — but CI only enforces 45%/40% coverage       |
| Security        | **C** | **CRITICAL dev-auth bypass** + disableable pipeline webhook auth      |
| Documentation   | C     | CLAUDE.md badly understates reality; orphan stacks (Flutter, Keycloak)|

**Overall:** the codebase is production-serious in tooling and hygiene, but has **two must-fix-before-prod issues** (dev-auth bypass and duplicate migration numbers) and a layer of accumulated cruft that's bleeding into reliability claims.

Counts that materially differ from CLAUDE.md:

| CLAUDE.md claim         | Reality                                  |
|-------------------------|------------------------------------------|
| 124 test files          | 233 files                                |
| ~1,300 test functions   | 3,364                                    |
| 21+ pages               | 60 pages                                 |
| 9+ hooks                | 116 hooks                                |
| 12 E2E specs            | 28                                       |
| 6 dims / 1 fact / 8 aggs| 8 dims / 6 facts / 14 aggs               |
| 28 routers / 40+ routes | 56 routers / 272 routes                  |
| 6 n8n workflows         | 8                                        |
| Coverage enforced ≥ 95% | CI enforces 45% unit / 40% integration   |
| 23 modules listed       | 40+ modules exist (12 undocumented)      |

---

## P0 — Must fix before next production deploy

### 1. CRITICAL — Dev-mode auth bypass
**File:** `src/datapulse/api/auth.py:162-182`

`get_current_user()` falls back to hardcoded dev claims (`tenant_id=1`, `roles=["viewer"]`) when both `api_key` and `auth0_domain` are empty. The only gate is a string check on `SENTRY_ENVIRONMENT not in ("development", "test")`. Any other value (`prod`, `production`, `staging`, unset default) lets unauthenticated callers through with fake claims.

**Fix:** explicitly allow-list the environments in which dev fallback is permitted (e.g. `SENTRY_ENVIRONMENT in ("development", "test")` AND `APP_ENV != "production"`), and hard-fail startup when both auth configs are empty outside dev.

### 2. HIGH — Duplicate migration numbers
**Files:** `migrations/031_*`, `migrations/088_*`, `migrations/089_*` (two files each)

- `031_gamification_tenant_fks.sql` + `031_pipeline_last_completed_stage.sql`
- `088_add_voucher_payment_method.sql` + `088_enforce_unique_pos_receipt.sql`
- `089_create_pos_vouchers.sql` + `089_tenant_scope_rls_owner_policies.sql`

A naive migration runner will apply only one of each pair and silently skip the other. If either was ever applied out-of-order on staging vs prod, the DBs have diverged.

**Fix:** renumber to 031a/031b or, better, renumber the later of each pair to the next free slot and verify that every environment has run both files.

### 3. HIGH — Pipeline webhook auth disableable via env var
**File:** `src/datapulse/api/auth.py:69-76`

`require_pipeline_token()` honours `PIPELINE_AUTH_DISABLED=true`. Combined with **no rate limiting** on pipeline mutation routes (`src/datapulse/api/routes/pipeline.py:98+`), a single misconfigured env var opens unlimited pipeline triggers (Bronze load, dbt marts, etc.).

**Fix:** remove the kill-switch or gate it behind `APP_ENV != "production"`, and add `@limiter.limit("5/minute")` on the pipeline POST routes (already the documented intent per CLAUDE.md).

### 4. HIGH — Coverage gate advertised at 95% but enforced at 45%/40%
**Files:** `pyproject.toml:85` (`fail_under = 95`) vs `.github/workflows/ci.yml` (`--cov-fail-under=45` unit, `40` integration)

CLAUDE.md and `pyproject.toml` promise 95%. CI won't fail a PR until coverage drops below 45%. The 233 test files / 3,364 tests suggest actual coverage is likely much higher than 45%, but the gate is meaningless as written.

**Fix:** either raise CI gates to the real floor (measure current and set to `current - 2`) or correct the claim in CLAUDE.md. Inconsistency is the bug.

---

## P1 — Structural debt

### 5. 5 business modules import from `api/`
Violates the layer rule in `.claude/rules/datapulse-graph.md`:

- `src/datapulse/rbac/dependencies.py:2` → `api.auth.get_current_user`
- `src/datapulse/billing/pos_guard.py:2-3` → `api.auth`, `api.deps`
- `src/datapulse/pos/devices.py:31` → `api.deps.get_tenant_session`
- `src/datapulse/pos/idempotency.py:42` → `api.deps.get_tenant_session`
- `src/datapulse/pos/overrides.py:39` → `api.deps.get_tenant_session`

These create import cycles waiting to happen. The session factory and `get_current_user` belong in `core/`; `api/deps.py` should only wire them into FastAPI.

### 6. 14 routes call repositories directly (skipping service layer)
Routes that bypass their service: `ai_light`, `anomalies`, `audit`, `billing`, `branding`, `gamification`, `insights_first`, `leads`, `notifications`, `onboarding`, `reseller`, `scenarios`, `targets`, `views`.

This means cache/authz/observability cross-cuts that live in the service layer don't apply to these features. Consolidate via service factories in `api/deps.py`.

### 7. POS domain is oversized
- `src/datapulse/pos/service.py` — **1,401 lines**
- `src/datapulse/pos/repository.py` — 1,187 lines
- `src/datapulse/pos/models.py` — 1,081 lines
- `src/datapulse/api/routes/pos.py` — 1,094 lines

CLAUDE.md target is 200–400 lines, extract at 800. Split POS into `terminal`, `transactions`, `shifts`, `vouchers` sub-services.

### 8. `create_app()` is 299 lines
**File:** `src/datapulse/api/app.py:67`

Router registration, middleware wiring, exception handlers, and startup hooks all in one function. Extract `register_routers(app)`, `install_middleware(app)`, `install_exception_handlers(app)`.

### 9. Orphan stacks at repo root
- `keycloak/realm-export.json` — project moved to Auth0; leftover config
- `flutter_app/` + `flutter_instructions.md` — coexists with an active Kotlin `android/` app; no doc clarifies which is canonical
- `LANGRAPH ai light plan.md` at repo root — belongs under `docs/plans/` or `docs/superpowers/plans/`

Decide each: archive, delete, or document.

---

## P2 — Security hardening

### 10. CORS wildcard + credentials is a configuration cliff
`src/datapulse/api/app.py:175-176` sets `allow_credentials=True`. `CORS_ORIGINS=["*"]` is possible because `src/datapulse/core/config.py:261-268` only *warns* on localhost in prod — it doesn't reject `*`. The combination is one typo away from credential-bearing CSRF.

**Fix:** validator rejects `*` when `allow_credentials=True`.

### 11. RLS write-window on dbt table creation
dbt creates tables first and applies `FORCE ROW LEVEL SECURITY` in post-hooks. If a dbt run crashes between creation and post-hook, the table exists briefly without RLS. The owner role would see cross-tenant data in that window.

**Fix:** create tables inside a transaction that also applies RLS, or use a scheduled "enforcement job" that verifies every marts table has `forcerowsecurity = true`.

### 12. JWT tenant_id claim fallback is unordered
`src/datapulse/api/auth.py:105-125` tries `https://datapulse.tech/tenant_id` → `tenant_id` → `tid` → `default_tenant_id`. A misconfigured Auth0 action that puts the claim under a different key silently routes to `default_tenant_id` instead of raising. For a multi-tenant app this is a cross-tenant data risk.

**Fix:** if NONE of the expected claims are present, raise 401. Don't fall back to a default tenant in production.

### 13. Upload ≈ 1 GB/min
`src/datapulse/api/routes/upload.py:74` allows 10 uploads/min × 100 MB each. No global disk quota. Per-tenant storage cap would be the clean fix.

### 14. `PIPELINE_AUTH_DISABLED` — see P0 #3.

---

## P3 — Data-layer polish

### 15. Financial precision drift
Primary standard is `NUMERIC(18,4)` (55+ uses). Outliers:
- `NUMERIC(18,2)` — 5 uses
- `NUMERIC(10,4)` — `cost_cents` in `migrations/049_create_ai_invocations.sql:13`
- `NUMERIC(8,4)`, `NUMERIC(5,2)` — misc

Standardize or explicitly justify each exception.

### 16. Bare `ALTER TABLE ADD COLUMN` in 4 migrations
`012_create_subscriptions.sql:18,23,28`, `028_create_resellers.sql:30`, `036_add_reseller_rls.sql:19`, `038_add_pipeline_heartbeat.sql:13`. They're inside DO blocks that catch duplicate-column exceptions, but that's fragile — Postgres 16 supports `ADD COLUMN IF NOT EXISTS`. Use it.

### 17. RLS policy coercion mismatch
Some policies compare `tenant_id::text = current_setting('app.tenant_id')::text`, others use `NULLIF(current_setting(...), '')::INT`. Inconsistency invites edge-case bugs when the session var is empty, unset, or non-numeric. Pick one helper and use it everywhere.

### 18. Column-whitelist SQL defense is fragile
`src/datapulse/bronze/loader.py:33-40` blocks SQLi by whitelisting `ALLOWED_COLUMNS`. Solid today, but if `COLUMN_MAP` drifts the protection silently degrades. Add a unit test asserting `set(COLUMN_MAP.values()) <= ALLOWED_COLUMNS`.

---

## P4 — Hygiene

### 19. TypeScript check blocked on missing vitest types
`npx tsc --noEmit` fails immediately with "Cannot find type definition file for `vitest/globals`". Either `npm ci` isn't installing `@vitest/globals` or tsconfig.json lists it incorrectly. Fix so the developer "run before push" command actually works.

### 20. ESLint on legacy config
`.eslintrc.json` + ESLint 10 doesn't run. Either migrate to `eslint.config.js` (flat) or pin ESLint to 8.x.

### 21. Docs drift
`CLAUDE.md` understates scope 2–3× across tests, pages, hooks, and module count. Twelve modules aren't listed at all: `control_center`, `brain`, `core`, `dispensing`, `expiry`, `insights_first`, `inventory`, `leads`, `pos`, `purchase_orders`, `scheduler`, `suppliers`. Either auto-generate the module list or regenerate CLAUDE.md on each release.

### 22. `print()` in 3 CLI utilities
13 calls across `brain/migrate_csv.py`, `bronze/__main__.py`, `graph/indexer.py`. Acceptable in CLIs, but `bronze/__main__.py` is pipeline-critical — switch to structlog so the single print doesn't dodge JSON log collection.

### 23. Monitoring stack has no healthchecks
Prometheus, Grafana, Alertmanager in `docker-compose.monitoring.yml` have no `healthcheck:`. Autoheal won't restart them when stuck. 5-minute fix.

### 24. No git tags
Deploy workflow is triggered by `push tags: v*` (`deploy-prod.yml`), but `git tag` returns nothing. Either the team deploys exclusively via manual `workflow_dispatch` (fine — document it) or tagging has been skipped (fix the release flow).

---

## Verified as safe

These claims were checked and hold up:

- Upload path traversal — UUID-only filenames + `Path.resolve().is_relative_to()` block `../` and symlink attacks (`src/datapulse/upload/service.py`, `bronze/loader.py:53`).
- JWT validation — exp/aud/iss/algorithms all enforced, RS256 pinned, azp checked (`src/datapulse/api/jwt.py:125-165`).
- Frontend `dangerouslySetInnerHTML` — only hardcoded print CSS, no user data.
- Docker port bindings — all services bound to `127.0.0.1` across every compose file.
- Base images — all pinned (no `:latest`).
- Resource limits — set on every core and prod service.
- Pydantic — fully on v2 `model_config = ConfigDict(...)`.
- 0 TODO/FIXME/HACK markers across `src/`, `frontend/src/`, `dbt/`.
- Graph MCP + Brain MCP — registered and wired (`src/datapulse/graph/mcp_server.py`).
- Pre-commit — ruff, ruff-format, gitleaks, detect-private-key all configured.

---

## Suggested remediation order

1. **Today** — Fix CRITICAL P0 #1 (dev-auth bypass) with a one-line environment guard + a regression test.
2. **This week** — P0 #2 (renumber duplicate migrations), P0 #3 (remove pipeline-auth kill-switch + add rate limit), P0 #4 (align coverage gates with reality).
3. **Next sprint** — P1 structural debt: the 5 layer leaks, the 14 routes that skip services, POS splits. Use `dp_impact` from the graph MCP before each change.
4. **Backlog** — P2/P3/P4 polish, each an hour or less.

Every P0/P1 item has a named file and line number; no exploration required to start.
