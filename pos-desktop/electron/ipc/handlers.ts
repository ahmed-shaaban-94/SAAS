/**
 * Registers all ipcMain.handle() entries that back the ElectronAPI surface.
 * Call once from app.whenReady() after openDb() and createHardware().
 *
 * Design ref: docs/superpowers/specs/2026-04-17-pos-electron-desktop-design.md §4.3.
 */

import { ipcMain, app } from "electron";
import type { HardwareBundle } from "../hardware/index";
import type Database from "better-sqlite3";

import { searchProducts, getProductByCode } from "../db/products";
import { getStockForDrug } from "../db/stock";
import {
  enqueueTransaction,
  getPendingQueue,
  getRejectedQueue,
  getQueueStats,
  reconcileTransaction,
} from "../db/queue";
import { getCurrentShift, openShift, closeShift } from "../db/shifts";
import { getSetting, setSetting } from "../db/settings";

export function registerIpcHandlers(
  db: Database.Database,
  hw: HardwareBundle,
): void {
  // ── db.products ────────────────────────────────────────────
  ipcMain.handle("db.products.search", (_e, q: string, limit?: number) =>
    searchProducts(db, q, limit),
  );

  ipcMain.handle("db.products.byCode", (_e, drugCode: string) =>
    getProductByCode(db, drugCode),
  );

  // ── db.stock ───────────────────────────────────────────────
  ipcMain.handle(
    "db.stock.forDrug",
    (_e, drugCode: string, siteCode: string) =>
      getStockForDrug(db, drugCode, siteCode),
  );

  // ── db.queue ───────────────────────────────────────────────
  ipcMain.handle("db.queue.enqueue", (_e, input: Parameters<typeof enqueueTransaction>[1]) =>
    enqueueTransaction(db, input),
  );

  ipcMain.handle("db.queue.pending", () => getPendingQueue(db));

  ipcMain.handle("db.queue.rejected", () => getRejectedQueue(db));

  ipcMain.handle("db.queue.stats", () => getQueueStats(db));

  ipcMain.handle(
    "db.queue.reconcile",
    (
      _e,
      localId: string,
      kind: "retry_override" | "record_loss" | "corrective_void",
      note: string,
      overrideCode: string | null,
    ) => reconcileTransaction(db, localId, kind, note, overrideCode),
  );

  // ── db.shifts ──────────────────────────────────────────────
  ipcMain.handle("db.shifts.current", () => getCurrentShift(db));

  ipcMain.handle(
    "db.shifts.open",
    (_e, payload: Parameters<typeof openShift>[1]) => openShift(db, payload),
  );

  ipcMain.handle(
    "db.shifts.close",
    (_e, payload: Parameters<typeof closeShift>[1]) => closeShift(db, payload),
  );

  // ── db.settings ────────────────────────────────────────────
  ipcMain.handle("db.settings.get", (_e, key: string) => getSetting(db, key));

  ipcMain.handle("db.settings.set", (_e, key: string, value: string) => {
    setSetting(db, key, value);
  });

  // ── printer ────────────────────────────────────────────────
  ipcMain.handle("printer.print", (_e, payload: unknown) =>
    hw.printer.print(payload as Parameters<typeof hw.printer.print>[0]),
  );

  ipcMain.handle("printer.status", () => hw.printer.status());

  ipcMain.handle("printer.testPrint", () => hw.printer.testPrint());

  // ── drawer ─────────────────────────────────────────────────
  ipcMain.handle("drawer.open", () => hw.drawer.open());

  // ── app ────────────────────────────────────────────────────
  ipcMain.handle("app.version", () => app.getVersion());

  ipcMain.handle("app.logsPath", () => app.getPath("logs"));

  // ── sync / authz / updater — deferred (require server coordination) ──
  ipcMain.handle("sync.pushNow", () => {
    throw new Error("sync.pushNow not yet implemented — M3 server wiring");
  });

  ipcMain.handle("sync.pullNow", () => {
    throw new Error("sync.pullNow not yet implemented — M3 server wiring");
  });

  ipcMain.handle("sync.state", () => ({
    online: false,
    last_sync_at: null,
    pending: 0,
    syncing: 0,
    rejected: 0,
    unresolved: 0,
  }));

  ipcMain.handle("authz.currentGrant", () => null);

  ipcMain.handle("authz.grantState", () => "offline_expired");

  ipcMain.handle("authz.refreshGrant", () => {
    throw new Error("authz.refreshGrant not yet implemented — requires online");
  });

  ipcMain.handle("authz.consumeOverrideCode", () => ({
    ok: false,
    reason: "authz not yet implemented",
  }));

  ipcMain.handle("authz.capabilities", () => {
    throw new Error("authz.capabilities not yet implemented — requires online");
  });

  ipcMain.handle("updater.check", () => ({ available: false }));

  ipcMain.handle("updater.install", () => {
    throw new Error("updater.install not yet implemented");
  });
}
