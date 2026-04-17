# 2026-04-17 — Phase 2 Golden Path shipped end-to-end

**Tags:** [[phase-2]] [[activation]] [[trust]] [[frontend]] [[api]] [[testing]] [[ci]]
**Epic:** [#398](https://github.com/ahmed-shaaban-94/Data-Pulse/issues/398) (closed by task completions)
**Tasks:** #399 / #400 / #401 / #402 / #403 / #404 / #405 — all shipped.
**PRs:** [#397](https://github.com/ahmed-shaaban-94/Data-Pulse/pull/397) chore + [#407](https://github.com/ahmed-shaaban-94/Data-Pulse/pull/407) [#408](https://github.com/ahmed-shaaban-94/Data-Pulse/pull/408) [#409](https://github.com/ahmed-shaaban-94/Data-Pulse/pull/409) [#410](https://github.com/ahmed-shaaban-94/Data-Pulse/pull/410) [#411](https://github.com/ahmed-shaaban-94/Data-Pulse/pull/411) [#412](https://github.com/ahmed-shaaban-94/Data-Pulse/pull/412) [#414](https://github.com/ahmed-shaaban-94/Data-Pulse/pull/414).

## The turn

Phase 1 ended with the positioning corrected (pharma-first landing, Pipeline Health rename, Lineage demote) but the actual **activation** path was still "drop a file and hope." Phase 2 turned that into a measurable, CI-gated golden path: a first-time pharma operator goes from `/upload` to a **non-empty first-insight card in under 5 minutes** — and CI now refuses to let that regress.

## Shipped

| Ticket | What's live on main | Lever |
|--------|---------------------|-------|
| [#399](https://github.com/ahmed-shaaban-94/Data-Pulse/issues/399) | Four TTFI events fire at their real seams (`upload_started` / `upload_completed` / `first_dashboard_view` / `first_insight_seen`) via `frontend/src/lib/analytics-events.ts`. PostHog capture + a stable `ttfi:event` window CustomEvent so tests/tooling can observe regardless of config. Baseline E2E (`golden-path-baseline.spec.ts`) measures without gating. | Activation |
| [#401](https://github.com/ahmed-shaaban-94/Data-Pulse/issues/401) | `src/datapulse/onboarding/sample_data.py` — deterministic 5k-row synthetic pharma dataset, idempotent via `source_file='sample.csv' + source_quarter='SAMPLE'`. `SampleLoadService` orchestrates pipeline_run + synthetic passing quality_checks. `POST /api/v1/onboarding/load-sample` rate-limited 5/min. | Activation + Trust |
| [#400](https://github.com/ahmed-shaaban-94/Data-Pulse/issues/400) | 3-step upload wizard (`WizardProgress`, `SampleDataCta`) composed into existing `upload-overview.tsx` via a `deriveStep` helper. Auto-redirects to `/dashboard?first_upload=1` on pipeline success. | Activation |
| [#402](https://github.com/ahmed-shaaban-94/Data-Pulse/issues/402) | `src/datapulse/insights_first/` — pure priority-based `pick_best()` + `FirstInsightService` + defensive fetchers. Shipped `top_seller` fetcher querying `bronze.sales` (30-day window). `GET /api/v1/insights/first` wraps result in `{insight: FirstInsight \| null}`. Dashboard `FirstInsightCard` (dismissable, `sessionStorage`-backed). | Activation + Trust |
| [#403](https://github.com/ahmed-shaaban-94/Data-Pulse/issues/403) | `EmptyState` gains `icon` + `action` slots (backward compatible). New `LoadSampleAction` + `UploadDataAction` components. Four pages migrated (Pipeline Health, Inventory, Expiry, Purchase Orders). | Clarity + Activation |
| [#404](https://github.com/ahmed-shaaban-94/Data-Pulse/issues/404) | `OnboardingStrip` — 4 steps auto-completing on `ttfi:event`, sharable-link step, self-hides when all done or >14 days old. `trackFirstInsightSeen` wired into the first-insight card (closes the Task 0 funnel). | Activation |
| [#405](https://github.com/ahmed-shaaban-94/Data-Pulse/issues/405) | `frontend/e2e/golden-path.spec.ts` — **hard CI gate: `TTFI < 5 min`**. Measures `first_insight_seen - upload_started` from the window event stream. `frontend/e2e/README.md` documents gate vs baseline. Sample CTAs now also fire `upload_completed` so the sample path makes the funnel whole. | Trust |

## Why the sequence worked

The dependency graph forced a specific order:

```
#399 (instrument) ──┐
                    ├── unblocked everything else by proving we could observe the funnel
#401 (sample data) ──┴── needed before the sample CTA had a real endpoint to call
#400 (wizard) ────────── needed before the first-insight card could reliably receive `?first_upload=1`
#402 (first-insight) ─── needed before the onboarding strip could fire `first_insight_seen`
#403 (empty states) ──── paralleled — no hard dependency on the others
#404 (strip) ─────────── closed the Task 0 funnel by wiring `trackFirstInsightSeen` from the card
#405 (E2E gate) ──────── required all of the above to be working end-to-end
```

We hit every dependency in order and every task fed the next without rework.

## Engineering lessons learned

### 1. Observability needs a non-conditional seam

The first cut of #407 shimmed `window.posthog.capture` in E2E. CI failed because `NEXT_PUBLIC_POSTHOG_KEY` is unset there, so the real `trackEvent()` returned early and the shim never fired. Fix: `analytics-events.ts` now **also** dispatches a `ttfi:event` window CustomEvent that fires regardless of config. Every TTFI test, including the hard gate in #414, uses this seam.

**Rule:** If a measurement matters for tests/CI, do not gate the emitter on runtime config. Emit to at least one always-on channel.

### 2. `npm audit fix` + CI npm version drift is a trap

The #397 chore PR originally used `npm audit fix`. Local CI passed; remote CI's `npm ci` rejected the regenerated lockfile because `npm audit fix` pruned a transitive (`@swc/helpers@0.5.21`) that the remote's older npm still required. The fix was:

- Use `package.json` `overrides` (surgical, declarative) for transitives.
- For direct deps that npm refuses to override (e.g. `next-intl`), bump `package.json` directly.
- Regenerate the lockfile with **the same npm major CI uses**: `npx npm@10.8.2 install --package-lock-only`.

**Rule:** Match the CI toolchain when generating lockfiles. `npx npm@X.Y.Z` is the lightest-weight way.

### 3. Scope decisions are PR-level content

Every Phase 2 PR explicitly stated what was **deferred** and why (e.g. remaining 56 empty-state migrations in #411; mom_change/expiry_risk/stock_risk fetchers in #410; backend `users.onboarding_state` sync in #412; dbt silver→gold in #408). Reviewers saw the cut and the reasoning in the same breath. Nothing got silently skipped.

**Rule:** If a scope cut is ambiguous, it's a bug. Write the carve-out into the PR body in the same paragraph as the feature summary.

### 4. A hard CI gate is cheap after the seam exists

`golden-path.spec.ts` is 130 lines. It works because all 7 prior tasks paid down the right seams: mockable endpoints, a window event channel, predictable redirects, a self-hiding card with an identifiable title, and an onboarding strip that tells you what auto-completed. The gate is expensive to **enable**, not to **maintain**.

## What's parked (good-timing follow-ups)

All recorded here, with self-contained kickoff prompts in [`docs/superpowers/plans/2026-04-17-phase2-followups.md`](../../superpowers/plans/2026-04-17-phase2-followups.md):

1. **Real droplet TTFI baseline runs** — `RUN_TTFI_BASELINE=1 ×5` against the droplet; fill the numbers in `docs/brain/incidents/2026-04-17-ttfi-baseline.md`.
2. **Richer first-insight fetchers** — `mom_change`, `expiry_risk`, `stock_risk`. Picker + service already accept them; one fetcher per PR.
3. **Empty-state migration to the shared pattern** — 56 remaining sites; one-PR-per-domain is healthiest.
4. **Backend onboarding-state sync** — promote the onboarding strip dismissal + first-insight dismissal from `localStorage`/`sessionStorage` to `users.onboarding_state` for cross-device UX.
5. **LLM-backed insight narrative** — Phase 8, not a Phase 2 follow-up, but the rule-based picker should feed it when it lands.

## Final Phase 2 verdict

Success metric shipped: `TTFI < 5 min` enforced on every future PR by `golden-path.spec.ts`. The onboarding flow went from "drop a file, hope for the best" to "one click, five minutes, three completed milestones, one signed-for-today insight." The emotional arc has a measurement and a gate.

## Linked layers

- [[layers/api]] — `insights_first` module, `onboarding.load-sample` route.
- [[layers/frontend]] — wizard + card + strip + shared empty-state action pattern.
- [[layers/test]] — baseline + gated E2E specs, TDD across every task.
- [[modules/onboarding]] — extended with sample_data + sample_service.
- [[modules/analytics]] — `ttfi:event` window emitter made the whole Phase 2 instrumentable.
