# 2026-04-17 — TTFI baseline (Phase 2, Task 0 / #399)

**Tags:** [[phase-2]] [[frontend]] [[analytics]] [[posthog]] [[onboarding]]
**Issue:** [#399](https://github.com/ahmed-shaaban-94/Data-Pulse/issues/399) · **Epic:** [#398](https://github.com/ahmed-shaaban-94/Data-Pulse/issues/398)
**Status:** Instrumentation shipped; numbers pending first droplet run.

## What was shipped

Four PostHog events at the golden-path seams, fired via idempotent helpers in `frontend/src/lib/analytics-events.ts`:

| Event | Fires at | Properties |
|---|---|---|
| `upload_started` | `/upload` mount (UploadOverview) | `ttfi_seam` |
| `upload_completed` | Pipeline `progress.status === "success"` (UploadOverview) | `run_id`, `duration_seconds`, `rows_loaded`, `ttfi_seam` |
| `first_dashboard_view` | `/dashboard` mount | `ttfi_seam` |
| `first_insight_seen` | Helper only — emitter live, caller lands with Task 3 (#402) | `kind`, `confidence`, `ttfi_seam` |

Guards: first-of-session via `sessionStorage`; `upload_completed` dedups per `run_id`.

Every event is stamped with `ttfi_seam: <event-name>` so a PostHog funnel can filter to golden-path events only and ignore unrelated captures.

## How to run the baseline on the droplet

The Playwright spec `frontend/e2e/golden-path-baseline.spec.ts` has two modes:

1. **Events-fire-in-order (always-on)** — three tests that use Playwright route mocks + a shimmed `window.posthog.capture`. These run on every CI build and gate PRs. They do not measure TTFI — they only prove the instrumentation fires at the right seams.
2. **TTFI measurement (droplet only)** — gated on `RUN_TTFI_BASELINE=1`. Walks `/upload → /dashboard` against a live backend, writes `playwright-report/ttfi-baseline.json` with per-event deltas from `t=0`.

### Droplet run

```bash
ssh root@<DROPLET_IP>
cd /opt/datapulse
# Ensure a tenant has no data so onboarding is fresh:
docker exec -it datapulse-db psql -U postgres datapulse \
  -c "DELETE FROM bronze.sales WHERE tenant_id = <TENANT>;"
cd frontend
RUN_TTFI_BASELINE=1 CI=1 npx playwright test e2e/golden-path-baseline.spec.ts \
  --project chromium --reporter=html
# Results:
cat playwright-report/ttfi-baseline.json
```

Run **5 consecutive times** and record the median + p95 in the table below.

## Baseline numbers (TBD — fill in after first droplet run)

| Run | `upload_started → upload_completed` | `upload_completed → first_dashboard_view` | Full TTFI (`upload_started → first_insight_seen`) | Notes |
|---|---|---|---|---|
| 1 | — | — | — | |
| 2 | — | — | — | |
| 3 | — | — | — | |
| 4 | — | — | — | |
| 5 | — | — | — | |
| **Median** | — | — | — | |
| **p95** | — | — | — | |

### Interpretation guide (pre-mortem)

- **Before Phase 2 ships (now):** `first_insight_seen` will **not fire** — there is no first-insight card yet (Task 3 / #402). Expect `ttfi_ms` in the JSON to be `null`. The deltas we can measure are `upload_started → upload_completed` and `upload_completed → first_dashboard_view`. That is still the baseline we must beat.
- **Expected range for today's UX** (educated guess, to be replaced with real numbers): 90–240 s for upload+pipeline with a 5 k-row file; 1–3 s for dashboard first paint. Phase 2 target: < 5 min end-to-end including a first-insight card.

## Why this matters

TTFI is the one number that says whether a first-time pharma operator can go from "I have a spreadsheet" to "I see a decision" without help. The whole Phase 2 plan ([docs/superpowers/plans/2026-04-17-phase2-golden-path.md](../../superpowers/plans/2026-04-17-phase2-golden-path.md)) optimizes it. Without a baseline recorded _before_ the wizard + first-insight card ship, "we improved the flow" becomes a feeling instead of a number.

Task 6 (#405) will convert this measurement into a CI-enforced assertion (`TTFI < 5 min`). This note is the predecessor.

## What's deliberately NOT in this task

- **No UX changes.** Everything shipped here is purely additive instrumentation. Upload flow, dashboard, Pipeline Health — all unchanged.
- **No listener for `first_insight_seen`.** Emitter is exported and unit-tested; Task 3 (#402) will invoke it when the first-insight card mounts with content.
- **No PostHog funnel dashboard yet.** Once 5 droplet runs land the numbers, we build the funnel in PostHog and link it from this note.

## Files touched

- `frontend/src/lib/analytics-events.ts` — new helper module (12 unit tests, all green)
- `frontend/src/__tests__/lib/analytics-events.test.ts` — unit tests (TDD, written first)
- `frontend/src/components/upload/upload-overview.tsx` — 2 useEffect hooks, 6 lines of wiring
- `frontend/src/app/(app)/dashboard/page.tsx` — 1 useEffect hook, 3 lines
- `frontend/e2e/golden-path-baseline.spec.ts` — new spec (3 always-on tests + 1 gated measurement)
- `docs/brain/incidents/2026-04-17-ttfi-baseline.md` — this note

No backend changes. No schema changes. No new dependencies.

## Linked work

- [[phase-2-golden-path]] epic
- [[#400]] Upload Wizard (next in sequence)
- [[#402]] First-Insight Card (calls `trackFirstInsightSeen`)
- [[#405]] Golden-Path E2E + CI TTFI gate (promotes this baseline into an enforced assertion)
- [[modules/analytics]] — pre-existing PostHog plumbing reused
