# E2E tests (Playwright)

Browser-level tests run on every PR. They live in this directory and use
`playwright.config.ts` at the frontend root.

## Golden-Path gate

[`golden-path.spec.ts`](./golden-path.spec.ts) is the **TTFI gate**. It
enforces the Phase 2 success metric: a first-time user goes from
`/upload` to seeing a non-empty first-insight card in under **5 minutes**.

The spec walks:

1. `/upload` → fires `upload_started`
2. Click "Use sample pharma data" CTA → fires `upload_completed`
3. Redirect to `/dashboard?first_upload=1`
4. First-insight card renders with non-empty title → fires `first_insight_seen`
5. Computes `TTFI = first_insight_seen.at - upload_started.at`
6. Asserts `TTFI < 5 minutes`

Events are captured via the `ttfi:event` window CustomEvent that
[`frontend/src/lib/analytics-events.ts`](../src/lib/analytics-events.ts)
dispatches on every golden-path capture. Measurement is independent of
PostHog availability.

### Running locally

```bash
cd frontend
npx playwright test e2e/golden-path.spec.ts --reporter=html
# Open the trace viewer for the last run:
npx playwright show-report
```

If a run fails, the HTML reporter includes a trace, a screenshot, and
a short video by default (see `playwright.config.ts` → `use.trace`,
`use.screenshot`).

### Running against the droplet (with backend)

The same spec runs against a live backend. Pointing the app at the
droplet is done via the frontend's standard env config:

```bash
NEXT_PUBLIC_API_URL=https://staging.datapulse.example npx playwright test \
  e2e/golden-path.spec.ts
```

With a live backend the `page.route()` mocks still win — remove them
locally if you want to exercise the full stack.

### TTFI baseline (measurement, not a gate)

[`golden-path-baseline.spec.ts`](./golden-path-baseline.spec.ts) from
Phase 2 Task 0 / #399 is the baseline spec. It records raw timings to
`playwright-report/ttfi-baseline.json` without failing on a threshold.
Useful for answering "did we improve?" — rerun it after a wizard or
picker change.

## Authentication

In CI, `global-setup.ts` mints a NextAuth session cookie before tests
run so protected routes like `/dashboard` are accessible. Locally, the
real Auth0 flow runs — use a personal browser login before invoking
`playwright test`. Individual specs that need an unauthenticated
context (e.g. `auth.spec.ts`) override this via
`browser.newContext({ storageState: undefined })`.
