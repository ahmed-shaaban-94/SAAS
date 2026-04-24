# Key & Credential Rotation

> One runbook per credential DataPulse holds. Rotate on schedule *and* when any of these happen:
> - A team member with access leaves the project
> - A laptop is lost or compromised
> - A secret is ever echoed in logs, screenshots, error messages, or Git

> Audit of where each secret is stored lives in `1Password → DataPulse Vault`.

## Rotation schedule

| Credential | Cadence | Owner | Out-of-band trigger |
|---|---|---|---|
| Postgres `datapulse` app role password | 90 days | Tech lead | Team departure |
| Postgres `readonly` replica role | 90 days | Tech lead | Team departure |
| JWT signing secret (Clerk default, no rotation needed for Clerk itself) | — | — | Clerk manages |
| Stripe API secret key | 180 days | Founder | Stripe breach notice |
| Paymob API keys | 180 days | Founder | Paymob breach notice |
| InstaPay merchant credentials | 365 days | Founder | Bank contact change |
| Twilio (WhatsApp) auth token | 180 days | Tech lead | Twilio breach notice |
| Sentry DSN | 365 days | Tech lead | Leak in a client build |
| Embed signing secret | 90 days | Tech lead | Any embed consumer churn |
| GitHub Actions deploy SSH key | 180 days | Tech lead | Team departure |
| DigitalOcean API token | 180 days | Tech lead | Team departure |
| Admin `API_KEY` (service-to-service) | 90 days | Tech lead | Any |
| `PIPELINE_WEBHOOK_SECRET` | 180 days | Tech lead | Any |
| Backup encryption passphrase | Never (rotating invalidates old backups) | — | Only if confirmed compromised — then re-encrypt all retained backups |

## General rotation pattern

Every rotation follows the same 6 steps — only the *where to generate* and *where to update* change.

1. **Generate** the new credential in the provider's console (or `openssl rand -base64 48` for in-house secrets).
2. **Stage** it as a new env var `<NAME>_NEXT` or a new GitHub Actions secret with a `_next` suffix. Do not overwrite the live one yet.
3. **Dual-read** — deploy application code that accepts either the live or `_next` value. (Most providers support two active keys simultaneously so this step is a no-op for them; see per-credential notes.)
4. **Flip** — promote `_next` to primary by renaming the secret. Deploy. Verify `GET /health` stays green and a tenant login works.
5. **Revoke** the old value in the provider's console. For in-house secrets, remove the old env var from every environment.
6. **Record** the rotation in `docs/brain/decisions/YYYY-MM-DD-rotate-<credential>.md`: date, reason, who did it, verification evidence.

If any step fails, **back out immediately** — return to step 4 with the old value and file a postmortem.

## Per-credential runbooks

### Postgres `datapulse` app role

```bash
# 1. Generate
NEW_PW=$(openssl rand -base64 32)

# 2. Stage as DATABASE_URL_NEXT (include in .env and CI secrets).
#    Existing app still reads DATABASE_URL.

# 3. Create the new password on the DB with ALTER USER (doesn't invalidate sessions).
psql "$DATABASE_URL_ADMIN" -c "ALTER USER datapulse WITH PASSWORD '$NEW_PW';"

# 4. Flip DATABASE_URL to the new password in env + CI secrets. Redeploy.
#    Because ALTER USER only affects new connections, the current connection pool
#    keeps working on the old password until the pool recycles (pool_recycle=1800s).
#    Wait > pool_recycle before step 5.

# 5. No revoke needed — ALTER USER replaces the password atomically.

# 6. Record.
```

### Postgres readonly replica role

Same pattern as above but against the replica host. Note: `DATABASE_REPLICA_URL` fallback (see PR #693) means even a botched rotation degrades to "serving reads from primary" — the fallback counter `datapulse_db_replica_fallbacks_total{reason="error"}` will spike.

### Stripe API key

Stripe supports **rolling keys**. Console → Developers → API Keys → Roll. Stripe keeps the old key live for 12 h by default.

1. Roll in Stripe console. Copy the new `sk_live_*`.
2. Update `STRIPE_SECRET_KEY` in GitHub Actions secrets and the prod `.env`.
3. Deploy. Watch Sentry for `stripe.error.AuthenticationError` for 10 min.
4. Done — Stripe auto-expires the old key after 12 h. No manual revoke.

### Paymob / InstaPay

Both require contacting merchant support to rotate. Email the new key request ≥ 1 week ahead of the schedule, then run a dev-mode end-to-end checkout on staging with the new key before flipping production.

### JWT / embed / pipeline-webhook / admin-api-key secrets

In-house HS256-style secrets. The app supports two active values during rotation:

- `<NAME>` — current, verified
- `<NAME>_NEXT` — new, also verified

If a route is wired to accept either, flip `<NAME>_NEXT` → `<NAME>` and drop the old one. If the route does not yet accept both (check the code before rotating), add dual-accept logic first, ship it, **then** rotate.

### GitHub Actions deploy SSH key

1. Generate locally: `ssh-keygen -t ed25519 -f /tmp/datapulse_deploy_next -C "gha-deploy-<YYYYMMDD>"`.
2. Add the new public key to `~/.ssh/authorized_keys` on the deploy target.
3. Update the `DEPLOY_SSH_KEY` secret in GitHub Actions with the new private key.
4. Trigger a manual deploy (`Actions → Deploy Production → Run workflow`). Confirm success.
5. Remove the old public key from `authorized_keys` on the target.
6. Delete the old private key from 1Password.

### DigitalOcean API token

Console → API → Tokens → generate new → revoke old once all GitHub workflows using it run green on the new token. No dual-accept needed — DO tokens are independent.

## Verification after any rotation

- [ ] `GET /health` on prod returns 200.
- [ ] A known-good test tenant logs in end-to-end.
- [ ] Sentry shows no new `Authentication*Error` or `InvalidToken*Error` for 15 min.
- [ ] For DB rotations: `datapulse_db_pool_checked_out` metric stays within normal band.
- [ ] For payment provider rotations: a sandbox checkout on staging clears with the new key before prod is touched.

## When to stop

Rotation is only valuable if the old credential is actually gone. If step 5 slipped through the cracks, the rotation was theater. Periodic audit: `rg '<old-secret-prefix>' -g '!*.md'` across the repo plus search the provider's "recent API calls with this key" to confirm zero activity post-revoke.

---

Reviewed with [on-call](oncall.md) and [DR drill](dr-drill.md) every quarter.
