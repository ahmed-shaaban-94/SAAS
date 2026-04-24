# Load testing — k6 scenarios (#607)

Baseline latency and throughput for the three request paths that matter
most on a live tenant:

| Scenario | What it hits | Why it matters |
|---|---|---|
| `dashboard.js` | `GET /api/v1/analytics/kpis` | Slowest hot-path; used on every dashboard open |
| `pos_checkout.js` | `POST /api/v1/pos/transactions/commit` | Latency here is customer-visible at the counter |
| `analytics_mixed.js` | 70/20/10 mix of KPIs, breakdown, trend | Representative read load |

## Requirements

- [k6](https://k6.io/docs/getting-started/installation/) ≥ 0.49 on `$PATH`
- A running DataPulse API (local `make up` or any staging URL)
- A valid JWT for the target tenant (see `env.example`)

## Running

```bash
# 1. Copy env template and fill in a JWT for the tenant you want to hit.
cp scripts/loadtest/env.example scripts/loadtest/.env
$EDITOR scripts/loadtest/.env

# 2. Load env, run a scenario (from repo root).
export $(grep -v '^#' scripts/loadtest/.env | xargs)
make loadtest-dashboard           # ~1 min — 10 VUs for 60 s
make loadtest-checkout            # ~1 min — 5 VUs (simulate 5 cashiers)
make loadtest-analytics-mixed     # ~2 min — ramp 0 → 20 VUs
make loadtest-all                 # run all three back-to-back
```

Or invoke k6 directly for ad-hoc tweaks:

```bash
k6 run \
  -e BASE_URL=$BASE_URL \
  -e AUTH_TOKEN=$AUTH_TOKEN \
  -e TENANT_ID=$TENANT_ID \
  scripts/loadtest/scenarios/dashboard.js
```

## Thresholds

Each scenario enforces p95 latency + error-rate thresholds via k6's
built-in `thresholds` block. If a run breaches them k6 exits non-zero,
so the same scripts can be wired into CI against a staging env once
credentials are provisioned.

Current baselines (captured on `main` @ branch merge time, 4-vCPU / 8 GB
single API container, colocated Postgres):

| Scenario | p50 | p95 | p99 | Error rate |
|---|---|---|---|---|
| `dashboard.js` | tbd | tbd | tbd | 0% |
| `pos_checkout.js` | tbd | tbd | tbd | 0% |
| `analytics_mixed.js` | tbd | tbd | tbd | 0% |

> Fill the table in after the first clean staging run — leaving `tbd`
> so a reviewer can see the shape and refuse to merge numbers without
> proof. The thresholds in each `.js` file match these targets.

## CI integration (deferred)

This PR ships the harness only; it does **not** add a CI job. Wiring a
nightly smoke-size run against staging is a follow-up that needs:

- A dedicated staging JWT provisioned as `LOADTEST_AUTH_TOKEN` secret
- A GitHub Actions workflow running `make loadtest-smoke` and failing
  on >20% p95 regression vs the table above
- A Grafana Tempo/SigNoz link in the PR output for regression triage

See issue #607 for the full acceptance criteria.
