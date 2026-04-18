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
 * Design ref: docs/superpowers/specs/2026-04-17-pos-electron-desktop-design.md §2.4.
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
let pendingWindow: BrowserWindow | null = null;

function send(win: BrowserWindow | null, event: UpdaterEvent): void {
  win?.webContents?.send("updater:event", event);
}

export function setupUpdater(win: BrowserWindow): void {
  pendingWindow = win;

  autoUpdater.autoDownload = true;
  autoUpdater.autoInstallOnAppQuit = false;

  autoUpdater.on("checking-for-update", () => {
    send(win, { type: "checking" });
  });

  autoUpdater.on("update-available", (info) => {
    send(win, { type: "available", version: info.version });
  });

  autoUpdater.on("update-not-available", () => {
    send(win, { type: "not-available" });
  });

  autoUpdater.on("download-progress", (progress) => {
    send(win, { type: "downloading", percent: Math.round(progress.percent) });
  });

  autoUpdater.on("update-downloaded", (info) => {
    updateReadyToInstall = true;
    send(win, { type: "ready", version: info.version });
    // Renderer receives this and shows an "Update ready — install at shift close?" dialog.
  });

  autoUpdater.on("error", (err: Error) => {
    send(win, { type: "error", message: err.message });
  });
}

/**
 * Run a silent update check. Call this after the 30s warm-up in main.ts so
 * the check doesn't compete with database init and sync startup.
 */
export async function checkForUpdates(): Promise<void> {
  try {
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

/**
 * Quit the app and apply the downloaded update immediately.
 * Only call after confirming the sync queue is empty.
 */
export function quitAndInstall(): void {
  autoUpdater.quitAndInstall(false, true);
}
