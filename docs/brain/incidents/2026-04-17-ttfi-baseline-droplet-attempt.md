# 2026-04-17 — TTFI droplet baseline attempt (follow-up #1)

**Tags:** [[phase-2]] [[deploy]] [[testing]] [[droplet]]
**Parent issue:** [#399](https://github.com/ahmed-shaaban-94/Data-Pulse/issues/399)
**Related plan:** [`docs/superpowers/plans/2026-04-17-phase2-followups.md`](../../superpowers/plans/2026-04-17-phase2-followups.md#follow-up-1--record-the-ttfi-baseline-on-the-droplet)
**Status:** Attempted, pivoted. New follow-up queued.

## What was attempted

Follow-up #1 from the Phase 2 follow-up prompts: "SSH to the droplet, run `golden-path-baseline.spec.ts` × 5, record median + p95 in [`2026-04-17-ttfi-baseline.md`](./2026-04-17-ttfi-baseline.md)."

## What actually happened

### Deployed main to the droplet (successful)

The droplet was ~35 PRs behind and its git remote still pointed at the old repo name (`ahmed-shaaban-94/SAAS.git`). Resolved:

1. Retargeted remote to `ahmed-shaaban-94/Data-Pulse.git` (same codebase, renamed).
2. Stashed prod-config drift (5 files: `docker-compose.monitoring.yml`, `docker-compose.prod.yml`, `monitoring/alertmanager.yml`, `nginx/default.conf`, untracked `nginx/monitoring.htpasswd`).
3. `git pull --ff-only origin main` — clean fast-forward, droplet now at commit [`dba2cc5`](https://github.com/ahmed-shaaban-94/Data-Pulse/commit/dba2cc5).
4. `git stash pop` — dropped all 4 tracked files' drift (they had been upstreamed into main via separate PRs between the droplet's last pull and today). Only `nginx/monitoring.htpasswd` (local/untracked) came back.
5. `docker compose build --no-cache api frontend` — both images built cleanly.
6. `docker compose up -d api frontend` — both containers recreated healthy.
7. `GET /health` → `{"status":"healthy"}`.
8. `GET /openapi.json | grep load-sample` → `/api/v1/onboarding/load-sample` registered.

Phase 2 + all follow-up fetchers are live on the droplet.

### Baseline spec runs — blocked

Two independent blockers surfaced when attempting the 5-run measurement:

1. **Database user not `postgres`.** The `DELETE FROM bronze.sales WHERE source_quarter='SAMPLE';` reset command failed with `FATAL: role "postgres" does not exist`. Discovering the actual user via `docker exec datapulse-db env | grep POSTGRES` was correctly refused by the harness's production-credentials guard.
2. **Playwright is not installed on the droplet.** The production frontend image ships only the Next.js standalone runtime (`node .next/standalone/server.js`). No `node_modules/.bin/playwright`, no Chromium binary. Running the spec would require either (a) installing ~700 MB of `node_modules` + Chromium onto the host, or (b) spinning up a sidecar `mcr.microsoft.com/playwright:v1.52.0-jammy` container with the frontend directory mounted.

### The deeper issue: the spec itself wouldn't have measured the right thing

`frontend/e2e/golden-path-baseline.spec.ts` uses `page.route()` to mock:

- `POST /api/v1/onboarding/load-sample`  (synthetic `{rows_loaded, pipeline_run_id, duration_seconds}`)
- `GET /api/v1/insights/first`            (synthetic `FirstInsight`)

With those mocks in place, the spec never hits the real backend. What it measures on the droplet is effectively the same thing it measures in CI or on a laptop: React `useEffect` mount timings inside a Chromium page. That produces numbers in the ~100–500 ms range regardless of where it runs. **Useful as a CI regression guard, not as a real TTFI measurement.**

## Lessons recorded as rules

1. **Pre-check the droplet's git remote before assuming `origin/main` is the deploy target.** `SAAS` → `Data-Pulse` rename was silent at the git-remote level. A one-line `git remote -v` at the start of a deploy-to-droplet flow saves minutes of "why didn't my PRs pull?"
2. **Production images don't have dev tooling by design.** A task that reads as "run the e2e spec on the droplet" implies a Playwright runner that isn't there. When scoping a droplet-run task, verify the runner exists (or decide to ship one) up front.
3. **Mocked specs don't measure what live specs measure.** If a task is "baseline the real flow," the spec must actually hit the real flow. A mocked baseline is valuable for CI but answers a different question.

## Pivot — what we're doing instead

Follow-up #1 as originally scoped is **closed as "attempted + pivoted."** Deploy work landed the updated code on the droplet; that alone is worth something (sample endpoint + fetcher trio + upload wizard + first-insight card now live on prod). The scope cut is: we don't have 5 droplet numbers.

New follow-up **#1b — real-backend TTFI baseline spec** queued. See the updated plan file below.

## Linked work

- [[layers/frontend]] — golden-path-baseline.spec.ts (mocked, shipped as a CI regression guard).
- [[layers/api]] — sample-load + insights/first endpoints now reachable on prod.
- [[phase-2-golden-path]] — epic #398 remains closed by the 7-task completion; this is post-hoc follow-up work.
