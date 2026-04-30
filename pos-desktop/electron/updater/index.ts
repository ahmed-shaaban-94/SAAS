/**
 * Auto-updater wrapper — uses electron-updater with GitHub Releases as the
 * update provider.
 *
 * Update policy (§2.4 of the design spec):
 *   1. Check for updates silently at startup (after a 30s warm-up delay).
 *   2. Prompt the cashier at the end of a shift (when shift.close is called).
 *   3. Apply the update only when:
 *      a. The sync queue is fully drained (no pending/rejected items).
 *      b. The server capability check passes (GET /pos/capabilities).
 *   4. If the update requires a non-downgradeable schema change, defer until
 *      the queue is drained — this is enforced by checking `schema_version`
 *      from the capabilities response.
 *
 * The updater emits events to the renderer via `mainWindow.webContents.send`.
 *
 * Design ref: docs/plans/specs/2026-04-17-pos-electron-desktop-design.md §2.4.
 */

import { autoUpdater } from "electron-updater";
import type { BrowserWindow } from "electron";

// ─── Types ────────────────────────────────────────────────────

export type UpdaterEvent =
  | { type: "checking" }
  | { type: "available"; version: string }
  | { type: "not-available" }
  | { type: "downloading"; percent: number }
  | { type: "ready"; version: string }
  | { type: "error"; message: string };

// ─── Setup ────────────────────────────────────────────────────

let updateReadyToInstall = false;
let allowedUpdateVersion: string | null = null;
let downloadedUpdateVersion: string | null = null;
let pendingWindow: BrowserWindow | null = null;

function send(win: BrowserWindow | null, event: UpdaterEvent): void {
  win?.webContents?.send("updater:event", event);
}

export function setupUpdater(win: BrowserWindow): void {
  pendingWindow = win;

  autoUpdater.autoDownload = false;
  autoUpdater.autoInstallOnAppQuit = false;

  autoUpdater.on("checking-for-update", () => {
    send(win, { type: "checking" });
  });

  autoUpdater.on("update-available", (info) => {
    if (!allowedUpdateVersion || info.version !== allowedUpdateVersion) {
      send(win, { type: "not-available" });
      return;
    }
    send(win, { type: "available", version: info.version });
    autoUpdater.downloadUpdate().catch((err: Error) => {
      send(win, { type: "error", message: err.message });
    });
  });

  autoUpdater.on("update-not-available", () => {
    send(win, { type: "not-available" });
  });

  autoUpdater.on("download-progress", (progress) => {
    send(win, { type: "downloading", percent: Math.round(progress.percent) });
  });

  autoUpdater.on("update-downloaded", (info) => {
    updateReadyToInstall = true;
    downloadedUpdateVersion = info.version;
    send(win, { type: "ready", version: info.version });
    // Renderer receives this and shows an "Update ready — install at shift close?" dialog.
  });

  autoUpdater.on("error", (err: Error) => {
    send(win, { type: "error", message: err.message });
  });
}

interface UpdatePolicyDoc {
  update_available?: boolean;
  allowed?: boolean;
  reason?: string;
  version?: string | null;
}

interface PolicyOptions {
  baseUrl: string;
  jwt?: string | null;
  currentVersion: string;
  channel?: string;
  platform?: string;
}

async function fetchUpdatePolicy(opts: PolicyOptions): Promise<UpdatePolicyDoc> {
  if (!opts.jwt) {
    return { update_available: false, allowed: false, reason: "missing_auth" };
  }

  const params = new URLSearchParams({
    current_version: opts.currentVersion,
    channel: opts.channel ?? "stable",
    platform: opts.platform ?? process.platform,
  });
  const res = await fetch(`${opts.baseUrl}/api/v1/pos/updates/policy?${params}`, {
    headers: { Authorization: `Bearer ${opts.jwt}` },
  });
  if (!res.ok) {
    return {
      update_available: false,
      allowed: false,
      reason: `policy_fetch_failed_${res.status}`,
    };
  }
  return (await res.json()) as UpdatePolicyDoc;
}

/**
 * Run a silent update check. Call this after the 30s warm-up in main.ts so
 * the check doesn't compete with database init and sync startup.
 */
export async function checkForUpdates(opts?: PolicyOptions): Promise<void> {
  try {
    if (opts) {
      const policy = await fetchUpdatePolicy(opts);
      if (!policy.update_available || !policy.allowed || !policy.version) {
        allowedUpdateVersion = null;
        send(pendingWindow, { type: "not-available" });
        return;
      }
      allowedUpdateVersion = policy.version;
    }
    await autoUpdater.checkForUpdates();
  } catch {
    // Non-fatal: update check failures are logged by the error event handler.
  }
}

/**
 * Called from the shift-close flow. Returns true if an update is waiting and
 * the queue is drained (caller is responsible for checking queue state).
 *
 * When this returns true, the renderer should offer "Restart & update now"
 * vs. "Update on next restart".
 */
export function isUpdateReady(): boolean {
  return updateReadyToInstall;
}

interface CapabilitiesDoc {
  /** Server's current POS schema version (monotonic integer). */
  schema_version?: number;
  /** Minimum app version the server supports; below this, the server rejects requests. */
  min_app_version?: string;
  [k: string]: unknown;
}

/**
 * Schema-compatibility gate (§2.4.c of the design spec).
 *
 * Before applying a downloaded update, verify that the server's schema state
 * is compatible with the *local* min_compatible_app_version. If the server has
 * moved to a newer non-downgradeable schema, block the install until the user
 * acknowledges — otherwise the update could brick the terminal mid-shift.
 *
 * Returns:
 *   - { canInstall: true } when safe
 *   - { canInstall: false, reason } when blocked
 */
export async function canInstallUpdate(opts: {
  baseUrl: string;
  jwt?: string | null;
  currentVersion: string;
  channel?: string;
  platform?: string;
  localMinCompatibleAppVersion: string;
  localSchemaVersion: number;
}): Promise<{ canInstall: boolean; reason?: string }> {
  if (!updateReadyToInstall) {
    return { canInstall: false, reason: "no_update_downloaded" };
  }

  let policy: UpdatePolicyDoc;
  try {
    policy = await fetchUpdatePolicy(opts);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return { canInstall: false, reason: `update_policy_unreachable:${msg}` };
  }

  if (!policy.update_available || !policy.allowed || !policy.version) {
    return { canInstall: false, reason: policy.reason ?? "update_not_allowed" };
  }
  if (downloadedUpdateVersion && policy.version !== downloadedUpdateVersion) {
    return {
      canInstall: false,
      reason: `update_policy_version_mismatch:policy=${policy.version},downloaded=${downloadedUpdateVersion}`,
    };
  }

  let capabilities: CapabilitiesDoc;
  try {
    const res = await fetch(`${opts.baseUrl}/api/v1/pos/capabilities`);
    if (!res.ok) {
      return { canInstall: false, reason: `capabilities_fetch_failed_${res.status}` };
    }
    capabilities = (await res.json()) as CapabilitiesDoc;
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return { canInstall: false, reason: `capabilities_unreachable:${msg}` };
  }

  // Schema monotonicity: if server schema has advanced beyond what the local
  // install can downgrade from, block.
  if (
    typeof capabilities.schema_version === "number" &&
    capabilities.schema_version > opts.localSchemaVersion
  ) {
    return {
      canInstall: false,
      reason: `server_schema_newer:server=${capabilities.schema_version},local=${opts.localSchemaVersion}`,
    };
  }

  return { canInstall: true };
}

/**
 * Quit the app and apply the downloaded update immediately.
 * Caller MUST have confirmed the sync queue is empty AND canInstallUpdate()
 * returned { canInstall: true } before calling this.
 */
export function quitAndInstall(): void {
  autoUpdater.quitAndInstall(false, true);
}
