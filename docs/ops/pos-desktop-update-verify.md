# Verifying a POS Desktop auto-update reached a cashier

One-page runbook. Hand this to whoever supports the cashier workstations after a new `pos-desktop-vX.Y.Z` release ships.

> Companion: [`docs/RUNBOOK.md`](../RUNBOOK.md), [`docs/CLAUDE_REFERENCE.md`](../CLAUDE_REFERENCE.md)
>
> Update-policy design: `pos-desktop/electron/updater/index.ts` §2.4 of the design spec.

---

## When to use this

After any new `pos-desktop-vX.Y.Z` tag has been published, AND the production deploy that includes its registration migration (e.g. `123_register_pos_desktop_v2.sql`) has completed.

Use this to:

- **Confirm one cashier machine** received the update before declaring rollout success.
- **Diagnose** a cashier reporting "I didn't see the update prompt."
- **Force-trigger** an early check on a known machine for validation.

---

## 0 · Pre-flight (do this once per release, on YOUR laptop, not the cashier's)

Verify both halves of the rollout are actually live before troubleshooting any cashier:

```bash
# 1. The GitHub Release exists with the installer attached.
gh release view pos-desktop-v2.0.0 --repo ahmed-shaaban-94/Data-Pulse | head -20
# Should list a `DataPulse-POS-2.0.0-Setup.exe` asset and a `latest.yml` asset.

# 2. The DB row exists and is active.
ssh root@164.92.243.3 \
  "docker exec datapulse-db psql -U datapulse -d datapulse -c \
   \"SELECT version, channel, platform, rollout_scope, active FROM pos.desktop_update_releases WHERE version = '2.0.0';\""
# Should return one row: 2.0.0 | stable | win32 | all | t

# 3. The /policy endpoint returns the new version for a fake terminal.
# This requires a valid bearer for the tenant; usually easier to do step 4 on a real cashier.
```

If any of (1) or (2) is missing, the rollout itself is broken — fix that before debugging individual cashier machines.

---

## 1 · On the cashier machine — quick check

The fastest non-invasive check. Tells you "did this machine get the update prompt yet?"

1. **Open the DataPulse POS app** as the cashier normally would.
2. **Press `Ctrl+Shift+I`** to open Chrome DevTools (built into Electron).
3. **Console tab → Filter to `updater`** and look for these messages in order:

   | Console event | Meaning |
   |---|---|
   | `updater:event {type: "checking"}` | App is hitting `/policy` |
   | `updater:event {type: "available", version: "2.0.0"}` | Found a newer version, downloading in background |
   | `updater:event {type: "downloading", percent: NN}` | In progress |
   | `updater:event {type: "ready", version: "2.0.0"}` | Done — cashier will see prompt at shift close |
   | `updater:event {type: "not-available"}` | Either app already on 2.0.0, or `/policy` says no |
   | `updater:event {type: "error", message: "..."}` | See §3 |

4. **App version (sanity)**: in DevTools console, type `electron.versions.app` (if exposed) or check **Help → About** in the app. Should show:
   - **Already updated**: `2.0.0`
   - **Pending update at shift close**: `1.0.1` (still old) but with a `ready` event in the log

If you see `ready` events, the cashier is good — the prompt fires when they close their next shift.

---

## 2 · Force-check now (skip the 30s warm-up)

If you want to manually trigger a `/policy` poll on a specific machine without restarting the app:

1. Open DevTools (`Ctrl+Shift+I`)
2. **Console** → run:
   ```js
   window.electron.updater.checkNow()
   ```
   *(if the IPC bridge exposes that method — check `pos-desktop/electron/preload.ts` for the exact name in the deployed build)*

If no IPC method is exposed, fall back to:

3. Quit the app fully (right-click tray icon → Quit, or Task Manager → end `DataPulse POS.exe`)
4. Reopen the app
5. Wait 30 seconds (the warm-up delay before the first `/policy` call)
6. Re-check console events as in §1

---

## 3 · Common failures + fixes

### `error: net::ERR_INTERNET_DISCONNECTED` or similar network errors

The cashier machine cannot reach `pos.smartdatapulse.tech` or `github.com`.

**Check**:
```cmd
:: From cmd on the cashier machine
ping pos.smartdatapulse.tech
ping github.com
```

**Fix**: usually a firewall / VPN / proxy issue at the pharmacy. The auto-updater pulls the actual installer file from GitHub Releases (`https://github.com/ahmed-shaaban-94/Data-Pulse/releases/download/...`), so GitHub must be reachable.

### `error: capabilities_fetch_failed_521`

The backend `/api/v1/pos/capabilities` endpoint is unreachable. This is the schema-compatibility gate.

**Cause**: production API is down, or behind a Cloudflare blip. Check `https://pos.smartdatapulse.tech/health` returns 200.

### `not-available` but you KNOW the new version is out

Either:

1. **App is already updated** — check Help → About. If it says 2.0.0, no action.
2. **`/policy` returned `update_available: false`** — most common cause is the migration row missing. Re-run the §0 pre-flight step 2.
3. **`/policy` returned `update_available: true` but version mismatch** — log shows `update_policy_version_mismatch:policy=X,downloaded=Y`. Means the policy row's version doesn't match what's on GitHub Releases. Check both.
4. **Tenant scoped out** — if the rollout row has `rollout_scope='selected'`, only tenants in `pos.desktop_update_release_targets` get it. Either add this tenant or change scope to `'all'`.

### `error: capabilities_unreachable` or similar

Same as above — backend reachability problem. Check `pos.smartdatapulse.tech` health.

### `ready` event fired but cashier never saw a prompt

The prompt is gated to **shift close** (so it doesn't interrupt mid-transaction). The cashier needs to:

1. Close their cash drawer / end their shift normally
2. The "Update ready — install at shift close?" dialog fires AFTER the shift-close confirmation

If they're stuck mid-shift indefinitely, the prompt won't appear. They can also force a manual install by closing the app cleanly (right-click tray → Quit) — the `autoInstallOnAppQuit` is **disabled** intentionally, so the user must explicitly trigger an install. If a force-update is needed, uninstall the old app + reinstall the new installer manually (next section).

---

## 4 · Manual install (escape hatch)

If auto-update is broken on one machine and you need that cashier on the new version *now*:

1. **Drain pending sync**: open POS, finish any in-flight transactions, ensure offline queue is empty (Status strip shows "● SYNCED · HH:MM").
2. **Quit the app cleanly**: right-click tray icon → Quit (NOT Task Manager kill — that may leave the SQLite DB in WAL state).
3. **Download the installer**:
   ```
   https://github.com/ahmed-shaaban-94/Data-Pulse/releases/download/pos-desktop-v2.0.0/DataPulse-POS-2.0.0-Setup.exe
   ```
4. **Run as Administrator** (per-machine install needs UAC).
5. **Existing install gets upgraded in place** — local SQLite DB at `%PROGRAMDATA%\DataPulse POS\` is preserved. NSIS installer's `oneClick: false` means it's interactive; click through the prompts.
6. **Launch** → Help → About → confirm `2.0.0`.
7. **Console** (Ctrl+Shift+I) → check no errors on first launch (especially around DB schema migration).

Manual install is functionally identical to the auto-updater path — same installer, same upgrade-in-place semantics.

---

## 5 · Confirming success at scale

To check rollout progress across ALL cashiers without visiting machines:

```sql
-- Run on production DB (read-only role is fine).
-- Requires the api to be logging shift-open events with app_version.
SELECT app_version, COUNT(DISTINCT terminal_id) AS terminals
FROM pos.terminal_sessions
WHERE created_at > now() - interval '24 hours'
GROUP BY app_version
ORDER BY app_version DESC;
```

You should see the v2.0.0 count rise + v1.0.1 fall over the days following the release as cashiers naturally close shifts and accept the install prompt.

If after 1 week any tenant's terminals are still 100% on v1.0.1, that's a signal something blocked their auto-update — start at §1 on one of those machines.

---

## 6 · Rollback (if v2.0.0 turns out broken)

This is destructive — only do this if v2.0.0 is causing real harm to live cashiers.

```sql
-- Pause the v2.0.0 rollout.
UPDATE pos.desktop_update_releases
SET active = false, updated_at = now()
WHERE version = '2.0.0' AND channel = 'stable' AND platform = 'win32';

-- Re-activate v1.0.1 so any new installs / fresh terminals land on the known-good version.
UPDATE pos.desktop_update_releases
SET active = true, updated_at = now()
WHERE version = '1.0.1' AND channel = 'stable' AND platform = 'win32';
```

This stops *new* `/policy` polls from finding v2.0.0. **It does NOT downgrade machines already on v2.0.0** — Electron auto-update is one-way. Downgrade requires manual uninstall + reinstall of v1.0.1 on each affected machine.

For that reason: write an [incident note](../brain/incidents/) before pausing, and [open a hotfix tag](#) (`pos-desktop-v2.0.1`) in parallel rather than relying on this rollback for long.

---

## Quick reference

| What | Where |
|---|---|
| Updater code | [`pos-desktop/electron/updater/index.ts`](../../pos-desktop/electron/updater/index.ts) |
| Policy endpoint code | [`src/datapulse/pos/update_policy.py`](../../src/datapulse/pos/update_policy.py) |
| DB schema | [`migrations/115_pos_desktop_update_rollouts.sql`](../../migrations/115_pos_desktop_update_rollouts.sql) |
| Release workflow | [`.github/workflows/pos-desktop-release.yml`](../../.github/workflows/pos-desktop-release.yml) |
| Release artifacts | https://github.com/ahmed-shaaban-94/Data-Pulse/releases |
| Stuck-deploy incident (the lesson behind the self-heal block) | [`docs/brain/incidents/2026-04-30-stuck-container-deploy-loop.md`](../brain/incidents/2026-04-30-stuck-container-deploy-loop.md) |
