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

## Real-backend TTFI runbook

[`golden-path-real-backend.spec.ts`](./golden-path-real-backend.spec.ts) measures
TTFI without any `page.route()` mocks — every request reaches a live backend. Use
this to get honest, production-representative latency numbers.

### Prerequisites

1. The droplet is deployed and accessible (e.g. `https://staging.datapulse.example`).
2. You have either:
   - **Option A** — a pre-minted NextAuth JWT (`PLAYWRIGHT_API_TOKEN`). Mint one on
     the droplet with: `docker exec datapulse-api python -c "import asyncio; from datapulse.api.test_utils import mint_playwright_token; print(asyncio.run(mint_playwright_token()))"`
   - **Option B** — the droplet's `NEXTAUTH_SECRET` value from its `.env` file.

### Running from a developer workstation

```bash
cd frontend

# Option A — pre-minted token:
RUN_TTFI_REAL=1 \
PLAYWRIGHT_BASE_URL=https://staging.datapulse.example \
PLAYWRIGHT_API_TOKEN=<jwt-from-step-above> \
TTFI_PASSES=5 \
npx playwright test e2e/golden-path-real-backend.spec.ts --reporter=list

# Option B — inline minting from NEXTAUTH_SECRET:
RUN_TTFI_REAL=1 \
PLAYWRIGHT_BASE_URL=https://staging.datapulse.example \
PLAYWRIGHT_NEXTAUTH_SECRET=<droplet-secret> \
PLAYWRIGHT_TEST_TENANT_ID=1 \
TTFI_PASSES=5 \
npx playwright test e2e/golden-path-real-backend.spec.ts --reporter=list
```

Results land in `playwright-report/ttfi-real.json`. Record median and p95 in
[`docs/brain/incidents/2026-04-17-ttfi-baseline.md`](../../docs/brain/incidents/2026-04-17-ttfi-baseline.md).

### Running from Docker (no local Node needed)

```bash
# From project root:
RUN_TTFI_REAL=1 \
PLAYWRIGHT_BASE_URL=https://staging.datapulse.example \
PLAYWRIGHT_NEXTAUTH_SECRET=<droplet-secret> \
TTFI_PASSES=5 \
docker compose -f docker/docker-compose.playwright.yml run --rm \
  -v "$(pwd)/playwright-report:/app/playwright-report" playwright
```

The `docker/Dockerfile.playwright` image pre-installs Chromium via the official
Playwright base image — no separate `playwright install` step needed.

### What the spec does

1. Injects a valid NextAuth session cookie (no Auth0 round-trip needed).
2. Navigates to `/upload` → clicks "Use sample pharma data".
3. Waits for `/dashboard?first_upload=1` — the real pipeline runs on the server.
4. Waits for the first-insight card title to be non-empty.
5. Computes `TTFI = first_insight_seen.at − upload_started.at`.
6. Writes `playwright-report/ttfi-real.json` with per-pass deltas, median, p95.
7. Asserts `TTFI < 5 min` per pass (same gate as the mocked CI spec).

### Populating the baseline document

After 5 successful passes, copy median + p95 from `ttfi-real.json` into:

```
docs/brain/incidents/2026-04-17-ttfi-baseline.md  →  ## Measured Results table
```

## Authentication

In CI, `global-setup.ts` mints a NextAuth session cookie before tests
run so protected routes like `/dashboard` are accessible. Locally, the
real Auth0 flow runs — use a personal browser login before invoking
`playwright test`. Individual specs that need an unauthenticated
context (e.g. `auth.spec.ts`) override this via
`browser.newContext({ storageState: undefined })`.
