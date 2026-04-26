---
date: 2026-04-26
severity: critical-outage
area: devops / auth / frontend
duration: ~1h (07:30–08:30 UTC)
services: [api, frontend, nginx, cloudflare]
commit-range: "37f5bb7...7ebac18 (160 commits behind)"
related_prs: [614]
---

# Production site down: Cloudflare 521 + Auth0 UI after Clerk deploy drift

## Symptom

`smartdatapulse.tech` returned HTTP 521 (Web Server is down) for ~20 minutes, then recovered to HTTP 200 but displayed the legacy Auth0 login screen instead of the migrated Clerk UI. Root cause was three layered failures masked by an out-of-band partial recovery and 160-commit deploy drift on the droplet.

## Layer 1: Containers in `Created` state

Someone (no log captured) ran `docker compose down` then `docker compose create` (or partial `up -d`) ~20 min before the outage was reported. The database, Redis, and API containers came up healthy, but `datapulse-frontend` and `datapulse-nginx` stayed in `Created` state and never started. Since nothing bound to host ports 80/443, Cloudflare's healthcheck failed and returned 521.

## Layer 2: nginx crash-loop on missing grafana upstream

After manually starting the frontend container, nginx entered a crash-loop (`RestartCount` climbed to 13) because its config referenced upstream `grafana:3000`, but the monitoring stack (`docker-compose.monitoring.yml`) was offline, so that container didn't exist in the docker network. nginx crashed on startup with `nginx: [emerg] host not found in upstream "grafana:3000"`.

Workaround: edited `/opt/datapulse/nginx/default.conf` to point the grafana upstream at `127.0.0.1:65535` (a non-existent address that resolves at startup but is unreachable at request time). nginx then started cleanly, and the site returned HTTP 200.

## Layer 3: Auth0 UI instead of Clerk (deploy drift)

The droplet's `/opt/datapulse` git was on commit `37f5bb7`, while `origin/main` was at `7ebac18` (160 commits ahead). Both the frontend and API container images were pre-Clerk: frontend was running the `:production` tag from 8 days ago (digest `sha256:73da1a76...`), API was running the `:staging` tag (digest `sha256:44709781...`). The Clerk swap landed in the gap as PR #614 and was completely absent from the deployed images.

Fix: pulled the latest `:production` images for both api and frontend, added `CLERK_*`, `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, and `NEXT_PUBLIC_AUTH_PROVIDER` env passthroughs to the `docker-compose.prod.yml` frontend service, edited `/opt/datapulse/.env` to set `NEXT_PUBLIC_AUTH_PROVIDER=clerk` and the Clerk keys, and recreated both containers.

Subtle bug during recovery: first attempt set env var `AUTH_PROVIDER=clerk`. Site still showed Auth0. The Next.js client reads `process.env.NEXT_PUBLIC_AUTH_PROVIDER` (with the `NEXT_PUBLIC_` prefix required for client-side visibility), not `AUTH_PROVIDER`. Without the prefix the var is invisible to the client bundle. Fix: renamed env var to `NEXT_PUBLIC_AUTH_PROVIDER`.

## Verification

- `https://smartdatapulse.tech/` returns HTTP 200
- `/sign-in` ships `@clerk/clerk-js` and references `clerk.accounts.dev` (not auth0domain)
- `/dashboard` (unauthenticated) redirects to `/sign-in?redirect_url=...` via Clerk's `<ProtectedPage>`, not to NextAuth `/login`
- Frontend container env exposes `NEXT_PUBLIC_AUTH_PROVIDER=clerk` and `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...`

## Outstanding tech debt

**Do NOT mark resolved — flag for follow-up PR.**

- **Test keys in production:** Droplet runs Clerk with test keys (`pk_test_…`/`sk_test_…`) on a production domain. Should migrate to a Clerk production instance with `pk_live_…` keys.
- **Leaked secret:** `sk_test_…` value was pasted in a chat transcript by user during recovery. Recommend rotating the key.
- **Stale Auth0 env vars:** `AUTH0_*` env vars still set in `.env` and passed through to containers. Harmless when `NEXT_PUBLIC_AUTH_PROVIDER=clerk`, but should be cleaned up.
- **Droplet 160 commits behind:** Working tree has uncommitted modifications to `nginx/default.conf`, three `docker-compose*.yml` files, and 30+ untracked migration files. A real `git pull` deploy needs cleanup first.
- **Migration schema drift:** Deployed repo has 123 migration files; DB `schema_migrations` table reports 129 rows. Six DB migrations exist in production but are not present in repo files — likely from commits the droplet hasn't seen.
- **nginx grafana stub:** Reverting the `127.0.0.1:65535` stub to `server grafana:3000;` after monitoring stack came up, but grafana access now depends on that stack staying running and being reachable on the docker network. Needs a proper upstream fallback or health-check logic.
- **Mixed image tags:** Before today, api was `:staging` and frontend was `:production`. Adds CI guard that refuses to deploy if running images don't match the `IMAGE_TAG` env at compose time.

## Lessons learned

- A crash-looping container behind `restart: unless-stopped` shows as `Up Less than a second (healthy)` for transient milliseconds. Truth lives in `docker inspect ... .State.Health.Status` and `RestartCount`.
- `docker-proxy` keeps host ports bound (`LISTEN`) even when its target container is dead. `ss -tln` showed 80/443 bound, but `curl localhost:80` got `Connection reset by peer`.
- The difference between `/login` and `/sign-in` was the highest-signal evidence for "wrong auth provider active." Neither HTTP status codes nor request logs made this obvious without examining the response body.
- Next.js `NEXT_PUBLIC_*` prefix is a silent failure mode: setting `AUTH_PROVIDER` instead of `NEXT_PUBLIC_AUTH_PROVIDER` produced "default to Auth0" with zero error messaging in logs.
