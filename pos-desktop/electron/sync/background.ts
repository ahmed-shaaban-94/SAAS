/**
 * Background sync loop (§6.1 push worker + §6.2 pull cadence).
 *
 * M3a: push-only loop (10s cadence). Pull (catalog) is M3b.
 * Boot recovery: reset orphaned `syncing` rows to `pending` on startup.
 */

import type { BrowserWindow } from "electron";
import type Database from "better-sqlite3";
import { drainQueue, getBaseUrl } from "./push";
import { checkOnline } from "./online";
import { getQueueStats } from "../db/queue";
import { getSetting } from "../db/settings";

const PUSH_INTERVAL_MS = 10_000;

let _timer: ReturnType<typeof setInterval> | null = null;
let _cleanup: (() => void) | null = null;

/**
 * Reset any `syncing` rows left by a previous crash back to `pending`.
 * The stored `device_signature` + `signed_at` mean the server idempotency key
 * still applies — duplicate processing is impossible.
 */
export function bootRecovery(db: Database.Database): void {
  const now = new Date().toISOString();
  const changed = db
    .prepare(
      `UPDATE transactions_queue SET status='pending', updated_at=? WHERE status='syncing'`,
    )
    .run(now);
  if (changed.changes > 0) {
    console.log(`[sync] boot recovery: reset ${changed.changes} orphaned syncing row(s) to pending`);
  }
}

/**
 * Start the background sync loop.
 * Returns a cleanup function that stops the loop (call from `app.on('before-quit')`).
 */
export function startBackgroundSync(
  db: Database.Database,
  mainWindow?: BrowserWindow | null,
): () => void {
  const tick = async () => {
    const baseUrl = getBaseUrl();
    const online = await checkOnline(baseUrl);

    if (online && getSetting(db, "terminal_id") && getSetting(db, "jwt")) {
      try {
        await drainQueue(db);
      } catch (err) {
        console.error("[sync] drainQueue error:", err instanceof Error ? err.message : err);
      }
    }

    // Push sync state to renderer so OfflineBadge + sync indicators update.
    if (mainWindow && !mainWindow.isDestroyed()) {
      const stats = getQueueStats(db);
      mainWindow.webContents.send("sync:state", { online, ...stats });
    }
  };

  _timer = setInterval(() => {
    tick().catch((err) => {
      console.error("[sync] tick error:", err instanceof Error ? err.message : err);
    });
  }, PUSH_INTERVAL_MS);

  // Run one tick immediately so state is fresh on startup.
  tick().catch(console.error);

  _cleanup = () => {
    if (_timer) {
      clearInterval(_timer);
      _timer = null;
    }
  };

  return _cleanup;
}
