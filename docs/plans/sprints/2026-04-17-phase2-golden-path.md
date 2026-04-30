# Phase 2 — Golden Path Sprint Plan

> **Lever:** Activation (primary) + Trust (secondary).
> **Source strategy:** [MASTER_CONVERSATION_REPORT.md §Phase 2](../specs/MASTER_CONVERSATION_REPORT.md) + [roadmap-filter.md](../active/roadmap-filter.md).
> **For agentic workers:** Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to execute task-by-task.

**Goal:** Turn the upload → dashboard → "one thing to act on" flow into the unmistakable product heartbeat. A first-time user should go from landing in the app to seeing a pharma-relevant decision cue in under 5 minutes.

**Success metric (pilot-facing):** Time-to-first-insight (TTFI) < 5 minutes for a user with a sample dataset loaded. Defined as: from hitting `/upload` to landing on a dashboard with a non-empty insight card.

**Not in scope:** Operations Suite cohesion (Phase 3), pilot package / billing (Phase 4 parallel track), lineage surfaces, external connectors.

---

## Working Context

- **Pharma-first landing** already shipped (PR #392) — messaging promises "upload spreadsheets, get decisions." This plan delivers on that promise.
- **Pipeline Health rename** shipped as part of this sprint's Option B — the activated user arrives to a dashboard they can trust.
- **Architecture:** Upload route already exists (`/upload`). Dashboard exists (`/dashboard`). The gap is the *seam* between them — what happens right after the user uploads? Right now: a redirect with no guidance. After this plan: a guided hand-off with a clear first-value moment.

---

## File Map (high-level)

| Area | Files likely touched |
|------|---------------------|
| Upload wizard UX | `frontend/src/app/(app)/upload/**`, `frontend/src/components/upload/**` |
| First-value insight card | new `frontend/src/components/dashboard/first-insight-card.tsx` |
| Empty states | `frontend/src/components/*/empty-state.tsx` — audit all, standardize |
| Executive dashboard header | `frontend/src/app/(app)/dashboard/page.tsx`, `components/dashboard/header-insight.tsx` (new) |
| Sample dataset seeder | new `src/datapulse/bronze/sample_data.py` + API route `POST /api/v1/onboarding/load-sample` |
| Onboarding state | `src/datapulse/onboarding/` (already exists) — extend to track TTFI milestones |
| E2E coverage | new `frontend/e2e/golden-path.spec.ts` |

---

## Task 0: Measure Baseline TTFI

Before changing anything, instrument the current flow so we can prove we improved it.

- [ ] **Step 1:** Add analytics events for: `upload_started`, `upload_completed`, `first_dashboard_view`, `first_insight_seen` (no-op insight card today = never seen).
- [ ] **Step 2:** Write an E2E spec `frontend/e2e/golden-path-baseline.spec.ts` that walks a fresh user through upload → dashboard and records timings.
- [ ] **Step 3:** Run baseline against droplet, capture median TTFI. Record in `docs/brain/incidents/2026-04-17-ttfi-baseline.md`.

Done when: baseline number is recorded and the E2E runs green.

---

## Task 1: Upload Wizard — Guided Multi-Step

Replace the single-drop-zone upload page with a 3-step wizard that coaches the user.

- [ ] **Step 1:** Split `upload/page.tsx` into steps: `choose-source` → `map-columns` → `validate-preview`.
- [ ] **Step 2:** Add "Use sample pharma data" CTA on step 1 — one click loads a ~5k-row seeded dataset for immediate exploration without requiring the user's own file.
- [ ] **Step 3:** Column-map step shows detected vs. expected columns with confidence scores (reuse existing `type_detector.py` output).
- [ ] **Step 4:** Validate-preview step shows first 20 rows + any quality-check warnings surfaced from the Pipeline Health signal (not a link — inline).
- [ ] **Step 5:** On finish, redirect to `/dashboard?first_upload=1` so the next task can render the welcome insight.

Done when: golden-path E2E passes the wizard with sample data in < 90s.

---

## Task 2: Sample Dataset Seeder (Backend)

- [ ] **Step 1:** Create `src/datapulse/onboarding/sample_data.py` that inserts a curated 5k-row pharma dataset into `bronze.sales` for the current tenant. Idempotent (delete + reinsert scoped to `source='sample'`).
- [ ] **Step 2:** Add route `POST /api/v1/onboarding/load-sample` behind `get_current_user`. Returns `{"rows_loaded": int, "pipeline_run_id": UUID}`.
- [ ] **Step 3:** Kick off bronze → silver → gold pipeline run synchronously (demo-scale; it's 5k rows).
- [ ] **Step 4:** Unit tests: `tests/test_onboarding_sample_data.py` — tenant isolation, idempotency, row count.
- [ ] **Step 5:** Add to `quality_checks` table — seed run passes all gates by construction so the new user's Pipeline Health page looks healthy.

Done when: sample-load endpoint returns in < 15s on the droplet and the gold aggs populate.

---

## Task 3: First-Insight Card (Frontend)

A dashboard-level card that appears when `?first_upload=1` is present or when the user has not yet dismissed it.

- [ ] **Step 1:** Create `frontend/src/components/dashboard/first-insight-card.tsx` — a 1-card component that picks the highest-signal insight from:
  1. Biggest MoM revenue change (product or branch)
  2. Expiry risk (any SKUs expiring within 30 days)
  3. Stock risk (any SKUs below reorder point)
  4. Fallback: top-selling product this month
- [ ] **Step 2:** Backend picker endpoint `GET /api/v1/insights/first` — returns `{kind, title, body, action_href, confidence}`. Leverages existing analytics + anomaly modules.
- [ ] **Step 3:** Dismissable. Dismissal stored on `users.onboarding_state.first_insight_dismissed_at`.
- [ ] **Step 4:** Show "View more insights" link that deep-links to `/insights`.

Done when: a new user lands on `/dashboard?first_upload=1` and sees a non-empty, relevant card within 2s.

---

## Task 4: Empty State Audit

Every page the user might land on before data is loaded needs a single unified empty state.

- [ ] **Step 1:** Inventory existing empty states across all `(app)/*` pages. Expected ~15 pages.
- [ ] **Step 2:** Extract shared `<EmptyState>` component with props `{icon, title, body, primary_action}`.
- [ ] **Step 3:** Standardize primary action to either "Load sample data" (if no data in tenant) or "Upload your data" (if landed without going through onboarding).
- [ ] **Step 4:** Snapshot tests for each empty state.

Done when: every `(app)/*` page's empty state routes the user to a next action, and the same component is used everywhere.

---

## Task 5: Onboarding Checklist (Light-Touch)

Not a full gamification system — just a 4-item strip on the dashboard that tracks the golden path.

- [ ] **Step 1:** Add `frontend/src/components/dashboard/onboarding-strip.tsx`: horizontal 4-step progress showing ✓ Connect data → ✓ Validate → ✓ See first insight → ◻ Share with teammate.
- [ ] **Step 2:** Backend tracks steps on `users.onboarding_state` — reuse existing `src/datapulse/onboarding/` module.
- [ ] **Step 3:** Strip auto-hides after all 4 steps complete or after 14 days.
- [ ] **Step 4:** "Share with teammate" = copy-link action (stretch: email invite, defer to Phase 5).

Done when: a new user sees 3/4 auto-complete during the golden path and 1 remaining (share).

---

## Task 6: Golden-Path E2E Spec

- [ ] **Step 1:** Write `frontend/e2e/golden-path.spec.ts` that:
  1. Logs in as a brand-new tenant
  2. Clicks "Use sample pharma data"
  3. Walks the 3-step upload wizard
  4. Lands on dashboard
  5. Asserts the first-insight card is visible with non-empty title
  6. Asserts TTFI < 5 minutes
- [ ] **Step 2:** Run on CI. Block merge if TTFI regresses above target.

Done when: spec is green on droplet CI and TTFI assertion holds for 3 consecutive runs.

---

## Task 7: Verification Gate

Before declaring Phase 2 complete:

- [ ] `ruff check src/ tests/` clean
- [ ] `pytest --cov-fail-under=95` passes on droplet
- [ ] `pytest -m unit -x` passes locally
- [ ] `npx playwright test golden-path.spec.ts` green 3×
- [ ] Measured TTFI improvement vs. Task 0 baseline — target 50% reduction or < 5 min absolute
- [ ] PR description includes "Lever: Activation" per new PR template
- [ ] Brain note written: `docs/brain/decisions/2026-05-XX-golden-path-shipped.md`

---

## Dependencies & Handoff

- **Pipeline Engineer:** Tasks 2, 7 (sample-data seeder, quality gates on sample run)
- **Analytics Engineer:** Task 3 backend (first-insight picker logic)
- **Frontend Engineer:** Tasks 1, 3, 4, 5 (wizard, card, empty states, strip)
- **Platform Engineer:** Task 0 (analytics events), Task 7 gate wiring
- **Quality/Growth Engineer:** Task 6 (E2E), Task 7 (verification)

Parallelizable: Tasks 1 and 2 can run in parallel. Task 3 depends on Task 2 seeder being live. Task 6 depends on 1, 2, 3, 5.

Estimated duration: 3 weeks with 1 week float.

---

## Out of Scope (parked)

- Connector marketplace (Phase 6)
- Self-service dashboard builder (Phase 7)
- AI narrative summary on first-insight card — fall back to rule-based picker; defer LLM-backed version to Phase 8
- Multi-dataset onboarding — first upload only; users with multiple spreadsheets land in `/upload` for subsequent files
