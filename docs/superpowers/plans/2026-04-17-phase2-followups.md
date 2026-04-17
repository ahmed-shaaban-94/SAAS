# Phase 2 — Follow-up kickoff prompts

> **For a fresh Claude Code session.** Each section below is a **self-contained prompt** you can paste into a brand-new session to pick up one of the deferred Phase 2 follow-ups. Each prompt assumes the agent has never seen the prior conversation — it points to the source documents that explain the why and how.
>
> **Branching convention:** fresh worktree from `origin/main` each time. Same pattern the Phase 2 sprint used.
> ```bash
> cd C:/Users/Shaaban/Documents/GitHub/Data-Pulse
> git fetch origin main
> git worktree add -b claude/<task-slug> .claude/worktrees/<task-slug> origin/main
> cd .claude/worktrees/<task-slug>
> claude
> ```

## Shared preamble (paste at the top of every prompt below)

```text
You are continuing work on DataPulse, a pharma-first sales and operations analytics SaaS. Phase 2 (Golden Path Sprint) landed on 2026-04-17 — the upload → first-insight flow is live and CI-gated at TTFI < 5 min. This task is one of the deliberately-parked follow-ups.

Read in order before writing any code:
1. `CLAUDE.md` (project conventions, tooling, security)
2. `docs/brain/decisions/2026-04-17-phase-2-golden-path-shipped.md` (what shipped + what was parked + engineering lessons)
3. `docs/superpowers/plans/2026-04-17-phase2-golden-path.md` (original plan — for reference only; the sprint is done)
4. `docs/ROADMAP_FILTER.md` (the four-lever filter every PR must tick)
5. `.claude/rules/use-graph-mcp.md` and `.claude/rules/use-second-brain.md` (tooling rules)
6. `docs/brain/_INDEX.md` (recent session context)

Rules that must hold for every PR:
- TDD: write failing tests before production code (see `superpowers:test-driven-development`).
- `superpowers:verification-before-completion` before claiming done — run the actual verification command fresh in the same message as the claim.
- Every PR body ticks at least one Strategic Lever box per `docs/ROADMAP_FILTER.md`.
- Lint + type-check + test suite must be fresh-green locally before pushing. Specifically:
  - `ruff check src/ tests/` exit 0
  - `ruff format --check src/ tests/` exit 0
  - `pytest -m unit` green (2680+ tests, don't drop below)
  - `npx tsc --noEmit` exit 0 (frontend)
  - `npx vitest run` green
- If the change touches Python + frontend contracts, mirror the shape in `frontend/src/types/api.ts`.
- Do not merge your own PR. Stop when CI is green and the PR URL is posted.

Windows dev constraints:
- No local Docker → no end-to-end pipeline runs locally. Ship tests that work with mocked sessions; rely on droplet CI for the full stack.
- For npm operations that regenerate a lockfile, use `npx npm@10.8.2 …` to match CI's npm version. `npm audit fix` prunes transitives that CI rejects — use `package.json` `overrides` instead for transitives.
```

---

## Follow-up 1 — Record the TTFI baseline on the droplet

**Branch:** `claude/ttfi-baseline-droplet-run`
**Parent:** #399 (the instrumentation that made this measurable)
**Lever:** Trust (numbers that commit us to a curve)
**Size:** small; ~1 hour + droplet runs.

```text
[paste shared preamble]

Your task: run the `golden-path-baseline.spec.ts` spec five times on the droplet and record the numbers in `docs/brain/incidents/2026-04-17-ttfi-baseline.md`.

Scope
-----
1. Ensure the droplet has a clean tenant (no `bronze.sales` rows for the target tenant_id).
2. Run `RUN_TTFI_BASELINE=1 CI=1 npx playwright test frontend/e2e/golden-path-baseline.spec.ts --project chromium --reporter=html` five times.
3. Extract the median + p95 of each step timing from the five `playwright-report/ttfi-baseline.json` artifacts.
4. Edit the results table in `docs/brain/incidents/2026-04-17-ttfi-baseline.md`.
5. Open a tiny docs-only PR; lever is Trust; body includes the raw numbers for the 5 runs.

Do NOT change the spec or the instrumentation — if something is wrong with the measurement, open a separate PR with a failing test first.

Stop after the docs PR CI is green.
```

---

## Follow-up 2 — Add `mom_change` fetcher to the first-insight picker

**Branch:** `claude/insight-fetcher-mom-change`
**Parent:** #402 (picker + service already accept new fetchers)
**Lever:** Activation (stronger signal than `top_seller`)
**Size:** small; ~2–3 hours.

```text
[paste shared preamble]

Your task: add a `mom_change` fetcher to `src/datapulse/insights_first/` that picks the biggest month-over-month revenue change (product OR branch) for the current tenant, and wire it into the service factory in `src/datapulse/api/routes/insights_first.py`.

Scope
-----
1. Read `src/datapulse/insights_first/picker.py` and `src/datapulse/insights_first/service.py` to confirm the `Callable[[int], InsightCandidate | None]` contract.
2. Add a new function `fetch_mom_change_candidate(session, tenant_id) -> InsightCandidate | None` in `src/datapulse/insights_first/repository.py`.
   - Read from `public_marts.agg_sales_monthly` if it exists, else GROUP BY month from `bronze.sales`.
   - Compute absolute MoM change per product and per branch; pick the biggest by absolute percentage swing, tie-breaking by absolute revenue delta.
   - Confidence: scale by magnitude of change, clamped to [0.4, 0.95].
   - Title + body pharma-operator-friendly (e.g., "Paracetamol 500mg sales +42% MoM").
   - action_href: `/products?key=<material>` or `/sites?key=<site>` depending on which dimension won.
   - Defensive: return None on any soft failure.
3. Add the fetcher to `get_first_insight_service` factory in the route file.
4. Tests (TDD, written first):
   - `tests/test_insights_first_mom_fetcher.py` — happy path with mocked session, zero-rows returns None, exception path returns None, confidence clamping.
   - Priority ordering already covered in `test_insights_first_picker.py`; no edit needed there.
5. Verification per preamble.

Stop after the PR CI is green.
```

---

## Follow-up 3 — Add `expiry_risk` fetcher

**Branch:** `claude/insight-fetcher-expiry-risk`
**Parent:** #402
**Lever:** Activation + Trust (SKU about to expire ≈ money about to be lost)
**Size:** medium; depends on `expiry.batches` / `expiry` module state.

```text
[paste shared preamble]

Your task: add an `expiry_risk` fetcher to `src/datapulse/insights_first/` that flags SKUs expiring within 30 days.

Scope
-----
1. Inspect `src/datapulse/expiry/` (models, service, repository) to find the canonical "SKUs expiring soon" query.
2. Add `fetch_expiry_risk_candidate(session, tenant_id)`:
   - Prefer delegating to `ExpiryService` if one already exposes a "top SKUs expiring in 30 days" method; wire it through dependency injection cleanly.
   - Otherwise, write a direct SQL query against the batches table with LIMIT 1 by quantity-at-risk.
   - Confidence: higher when many SKUs are affected; cap 0.95.
   - action_href: `/expiry`.
3. Add to the service factory.
4. Tests (TDD) — mocked session or mocked ExpiryService, priority already covered.
5. Verification per preamble.

If the expiry module surface is fragmented, prefer writing a small direct SQL query rather than widening an existing service's public API. Justify the call in the PR body.

Stop after the PR CI is green.
```

---

## Follow-up 4 — Add `stock_risk` fetcher

**Branch:** `claude/insight-fetcher-stock-risk`
**Parent:** #402
**Lever:** Activation (stockouts are operator-critical)
**Size:** medium; similar shape to Follow-up 3.

```text
[paste shared preamble]

Your task: add a `stock_risk` fetcher for SKUs below their reorder point.

Scope
-----
1. Inspect `src/datapulse/inventory/reorder_service.py` + `reorder_repository.py`.
2. Add `fetch_stock_risk_candidate(session, tenant_id)` that returns the single highest-impact SKU at risk.
3. Wire into the service factory.
4. TDD tests.
5. Verification per preamble.

Stop after the PR CI is green.
```

---

## Follow-up 5 — Migrate remaining empty states to the shared pattern

**Branch:** `claude/empty-state-migration-wave-2`
**Parent:** #403 (established the pattern)
**Lever:** Clarity + Activation
**Size:** medium — expect one PR per domain if the surface is large.

```text
[paste shared preamble]

Your task: migrate the remaining bespoke empty-state renderings to the shared `<EmptyState>` + `<LoadSampleAction>` / `<UploadDataAction>` pattern introduced in #411.

Scope
-----
1. Run: `grep -rn "No data\|No .\+ yet\|Nothing to show\|flex flex-col items-center" frontend/src/components` to enumerate candidates.
2. Skip components already using `<EmptyState>` (the 4 migrated in #411 plus any others on main).
3. For each remaining candidate that is a pure "no data" render (not an error, not a form placeholder):
   - Replace the local render with `<EmptyState icon={...} title="..." description="..." action={<LoadSampleAction /> or <UploadDataAction />} />`.
   - Delete the now-unused local icon + styling.
4. Batch by domain, not globally: one PR for inventory, one for expiry, one for dispensing, one for dashboard cards, etc. Keeping each PR reviewable is more important than finishing in one round.
5. Snapshot tests: if a page has Vitest coverage already, extend it; do not create new test infrastructure just for this.

Do NOT refactor `<EmptyState>` itself — keep backward compatibility.

Stop after each domain PR goes green and is merged. Then open the next one. Track progress in a short checklist issue if it helps.
```

---

## Follow-up 6 — Backend sync for onboarding strip + first-insight dismissals

**Branch:** `claude/onboarding-state-cross-device`
**Parent:** #404 (introduced local-only persistence)
**Lever:** Trust (cross-device UX honesty)
**Size:** medium; backend + frontend + migration.

```text
[paste shared preamble]

Your task: promote the onboarding-strip completion state and the first-insight-card dismissal timestamp from local browser storage into `users.onboarding_state`, so state persists across devices and sessions.

Scope
-----
Schema
1. Add a migration: extend the existing `public.onboarding` table (see `migrations/017_create_onboarding.sql`) with two JSONB columns:
   - `golden_path_progress JSONB NOT NULL DEFAULT '{}'::jsonb` — mirrors the `OnboardingStrip` localStorage payload.
   - `first_insight_dismissed_at TIMESTAMPTZ NULL` — dismissal timestamp.
   Migration must be idempotent (`IF NOT EXISTS` guards).

API
2. New endpoints on the onboarding router:
   - `PUT /api/v1/onboarding/golden-path-progress` — upserts the JSONB.
   - `POST /api/v1/onboarding/dismiss-first-insight` — writes the timestamp.
   - Extend `GET /api/v1/onboarding/status` to return both fields.

Frontend
3. `OnboardingStrip` + `FirstInsightCard` read from `/api/v1/onboarding/status` on mount. Writes go through the new endpoints. Keep localStorage as a fast path and fallback; reconcile on mount.
4. No UX regressions on unauthenticated or degraded-backend cases — local storage still works.

Tests
5. TDD for: repository writes, service validation, route behavior, frontend hooks (sync + conflict resolution).

Security
6. RLS on both new columns (inherit from table policies). Migration must keep tenant scoping.

Stop after the PR CI is green. A small droplet smoke test (log in on two browsers, complete a step, reload the other) is worth doing manually before merge.
```

---

## Follow-up 7 — Reconcile onboarding step taxonomies

**Branch:** `claude/onboarding-steps-unify`
**Parent:** #404 (strip uses a different set of steps from existing OnboardingService)
**Lever:** Clarity
**Size:** small-to-medium; mostly a taxonomy decision + migration.

```text
[paste shared preamble]

Your task: decide whether the Phase 2 onboarding strip's 4 steps (`connect_data / validate / first_insight / share`) should unify with the existing `OnboardingService` steps (`connect_data / first_report / first_goal / configure_first_profile`) or remain parallel.

Scope
-----
1. Investigate the current `OnboardingService` callers (`src/datapulse/onboarding/` + any frontend hook that reads `/onboarding/status`).
2. Write a short ADR (`docs/adr/NNNN-onboarding-step-taxonomy.md`) arguing for ONE of:
   - **Merge**: rename/consolidate into a single step list; migrate existing rows.
   - **Keep parallel**: the onboarding-strip is a "golden path" concept distinct from the "onboarding wizard"; document the distinction and rename one to avoid confusion.
3. Implement the chosen path. If merging, include a migration + service refactor. If parallel, rename the Phase 2 localStorage key + component prop names so readers can't conflate them.

Ship the ADR in the same PR as the implementation (or in a separate "decisions first, code next" PR if the ADR is contentious).

Stop after CI green.
```

---

## Follow-up 8 — Fire `upload_completed` through the real pipeline path with the shared helper

**Branch:** `claude/upload-completed-shared-helper`
**Parent:** #405 (duplicated the trackUploadCompleted call across SampleDataCta + LoadSampleAction)
**Lever:** Clarity
**Size:** small; ~1 hour.

```text
[paste shared preamble]

Your task: extract the duplicated `trackUploadCompleted` post-endpoint call that lives in both `SampleDataCta` and `LoadSampleAction` (both in frontend/src/components) into a single helper, and reuse it anywhere else a sample-load succeeds.

Scope
-----
1. Grep the frontend for `postAPI<SampleLoadResult>` and `/api/v1/onboarding/load-sample`.
2. Extract a single hook or function — probably `frontend/src/hooks/use-load-sample.ts` — that:
   - Does the POST.
   - Fires `trackUploadCompleted` with the returned metadata.
   - Returns `{ loading, error, loadSample }` to the caller.
   - Optionally accepts a redirect destination override.
3. Migrate `SampleDataCta` + `LoadSampleAction` to use it.
4. Update their existing tests; no behavior change expected.
5. Verification per preamble.

Stop after CI green.
```

---

## Ordering recommendation

If someone takes on several of these at once, ship them in this order to maximize parallel-friendliness:

1. **Follow-up 1** (record baseline) — unblocks quantitative claims elsewhere.
2. **Follow-up 8** (shared helper) — cleans a duplication that will otherwise multiply as other CTAs get added.
3. **Follow-ups 2 → 3 → 4** (fetchers) — each is one PR; picker priority already favors mom > expiry > stock.
4. **Follow-up 5** (empty-state migration) — parallel to the fetchers, one PR per domain.
5. **Follow-up 7** (taxonomy ADR) — before backend sync in Follow-up 6 so sync is built on a decided schema.
6. **Follow-up 6** (backend sync) — last because it depends on the taxonomy decision.

Do NOT bundle. Each PR stays reviewable.
