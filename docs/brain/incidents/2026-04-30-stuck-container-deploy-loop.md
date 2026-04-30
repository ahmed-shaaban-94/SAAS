# Stuck-container deploy loop — 2026-04-30

**Severity:** P1 (production down ~50 min: 17:27 → 18:18 UTC)
**Surface:** Both `smartdatapulse.tech` and `pos.smartdatapulse.tech` returning nginx upstream errors / refused connections.
**Status:** Resolved by [PR #800](https://github.com/ahmed-shaaban-94/Data-Pulse/pull/800) (commit `13db99a1`) merging the self-heal block + cleanup workflow.

## Symptom

After PRs #797 and #798 merged in quick succession, the next Deploy Production run failed at the `compose up --force-recreate` step with:

```
Container 68441deb379a_datapulse-api Error response from daemon:
Error when allocating new name: Conflict.
The container name "/datapulse-api" is already in use by container "68441deb379a78c3...".
You have to remove (or rename) that container to be able to reuse that name.
```

The deploy script then triggered its rollback path. Rollback removed the *running* `nginx` and `frontend` containers but left `datapulse-api`, `datapulse-arq-worker`, `datapulse-redis`, `datapulse-db` running on the old `:staging` tag. Nginx was gone, so all external requests failed at the edge (upstream unreachable). The site was down.

Subsequent retries of Deploy Production hit the same conflict because the **stuck containers were now in `Created` state** (recreate started, never finished) and the next `--force-recreate` aborted before reaching the SSH-cleanup step. **Self-perpetuating loop** — every retry made the situation marginally worse.

## Root cause

Deploy script lacked an idempotency / self-heal block. `docker compose up --force-recreate` works fine on first run, but is not robust when a previous run was interrupted mid-recreate. Once any datapulse-* container is left in `Created` / `Exited` / `Dead` state, no future deploy can recover without manual SSH intervention.

## What surfaced it

- The shared Droplet hosts both staging and production (different image tags). Staging deploy auto-fires on every CI-on-main success; production is manual or tag-triggered.
- Two PRs (#797 visual port, #798 checkout fix) landed minutes apart. Each triggered a CI run which triggered staging. Compose under concurrent recreate pressure tripped on the conflict and never recovered.
- Postgres logs from the same window showed unrelated pre-existing query bugs (`column "updated_at" does not exist` on `marts.metrics_summary`, missing `stg_batches` relation) — noise, not the cause, but worth a separate fix in the analytics path.

## Fix

[PR #800](https://github.com/ahmed-shaaban-94/Data-Pulse/pull/800) merged at 18:03:27 UTC, commit `13db99a1`. Two changes:

### 1. Self-heal in `deploy-prod.yml` + `deploy-staging.yml`

Before `compose up --force-recreate`, scan for any `datapulse-*` container in `Created` / `Exited` / `Dead` state and `docker rm -f` it. Running containers are untouched (compose's own `--force-recreate` handles those).

```bash
STUCK=$(docker ps -a --filter 'name=datapulse-' --filter 'status=created' --format '{{.Names}}')
STUCK_EXITED=$(docker ps -a --filter 'name=datapulse-' --filter 'status=exited' --format '{{.Names}}')
STUCK_DEAD=$(docker ps -a --filter 'name=datapulse-' --filter 'status=dead' --format '{{.Names}}')
ALL_STUCK=$(echo "$STUCK $STUCK_EXITED $STUCK_DEAD" | tr ' ' '\n' | grep -v '^$' | sort -u)
if [ -n "$ALL_STUCK" ]; then
  echo "$ALL_STUCK" | xargs -r docker rm -f
fi
```

### 2. New `cleanup-droplet.yml` workflow

Weekly Sunday 04:00 UTC + on-demand. Prunes stale Docker images (>72h), stopped containers, BuildKit cache, unused networks, and `.env.bak.*` files (>7d) in `/opt/datapulse`. Never touches volumes (would destroy DB data). Has a `dry_run` toggle.

## Recovery timeline (UTC)

| Time | Event |
|---|---|
| 17:18 | PR #797 merged, CI fires |
| 17:27 | Deploy Production starts → fails on container conflict |
| 17:39 | Production rolled back, site down |
| ~17:55 | User reports "production fail" |
| 17:56 | First retry attempted — gated on staging which also failed |
| 18:00–18:02 | Diagnosis: SSH read-only inspection confirms two containers stuck in `Created` state |
| 18:03 | [PR #800](https://github.com/ahmed-shaaban-94/Data-Pulse/pull/800) merged with `--admin` (CI-only diff, low risk) |
| 18:13 | Deploy Staging fires automatically on PR #800's CI completion |
| 18:18 | Self-heal block runs, removes stuck containers, deploy succeeds → **site back up** |
| 18:22 | Deploy Production triggered manually to land production-tagged images |
| 18:31 | Deploy Production succeeds (9m2s, run `25182136501`); both domains 200 |

**Total downtime: ~51 minutes** (17:27 → 18:18 when staging deploy restored the site).

## What worked

- Read-only SSH inspection confirmed the stuck-container hypothesis cheaply
- `--admin` merge of PR #800 was justified (CI-only diff, no runtime code, production already down so risk-of-CI-fail was less than risk-of-extended-outage)
- Self-heal block proved itself on its first real run — staging recovered automatically without any further manual intervention
- Cleanup workflow is now in place to prevent the slow-bleed conditions (`.env.bak.*` accumulation, unreaped image layers) that compound over time

## What didn't work / lessons

- **Hook policy gates worked correctly** but cost time: a clearer phrasing of the production-touch authorization upfront would have unblocked the first SSH attempt instead of the third
- **Concurrent PR landings** are a known risk on a shared-Droplet single-deploy-target architecture. The migration plan toward managed infra (ECS Fargate or DO App Platform, see strategic discussion 2026-04-30) becomes more urgent each time this hits
- **No alerting** — the user discovered the outage manually. Sentry uptime checks fired but no human got paged. **First Phase-1 priority** in the migration plan
- **Image-tag drift**: during the outage the running API was on `:staging` while serving production traffic. Ran for ~50 min before being detected. Worth a healthcheck assertion that the running image tag matches the expected deploy tag

## Related

- [PR #797](https://github.com/ahmed-shaaban-94/Data-Pulse/pull/797) — POS visual port (was the trigger PR for the deploy that initially failed)
- [PR #798](https://github.com/ahmed-shaaban-94/Data-Pulse/pull/798) — POS checkout bulk-sync fix (deployed in same window)
- [PR #799](https://github.com/ahmed-shaaban-94/Data-Pulse/pull/799) — POS auth/idempotency hardening (landed minutes after #798, created a separate but coincident regression in the addItem path — see [PR #801](https://github.com/ahmed-shaaban-94/Data-Pulse/pull/801))
- [PR #800](https://github.com/ahmed-shaaban-94/Data-Pulse/pull/800) — **the fix** (self-heal + cleanup workflow)
- [PR #801](https://github.com/ahmed-shaaban-94/Data-Pulse/pull/801) — addItem Idempotency-Key + drug_code coercion (different incident, surfaced same evening)

## Follow-ups

- [ ] Run `cleanup-droplet.yml` in dry-run mode to validate output before first scheduled run
- [ ] Address Postgres query bugs in `marts.metrics_summary` and `stg_batches` paths (separate issue, found in incident logs)
- [ ] Consider adding a deploy-image-tag drift check in nightly health monitoring
- [ ] Phase 1 of infra migration: Sentry traces + APM (would have paged on the outage)
