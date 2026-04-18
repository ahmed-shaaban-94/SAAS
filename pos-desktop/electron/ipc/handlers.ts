/**
 * Registers all ipcMain.handle() entries that back the ElectronAPI surface.
 * Call once from app.whenReady() after openDb() and createHardware().
 *
 * Design ref: docs/superpowers/specs/2026-04-17-pos-electron-desktop-design.md §4.3.
 */

import { ipcMain, app } from "electron";
import { randomUUID } from "node:crypto";
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
import { drainQueue, buildEnqueueSignature, getBaseUrl } from "../sync/push";
import { pullCatalog } from "../sync/pull";
import { isOnline } from "../sync/online";
import { isDeviceRegistered, registerDevice } from "../authz/device";
import { currentGrant, grantState, consumeOverrideCode, refreshGrant } from "../authz/grants";

const COMMIT_PATH = "/api/v1/pos/transactions/commit";

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
  ipcMain.handle(
    "db.queue.enqueue",
    (
      _e,
      input: {
        endpoint: string;
        payload: unknown;
        auth_mode: "bearer" | "offline_grant";
        grant_id: string | null;
      },
    ) => {
      const clientTxnId = randomUUID();
      const signedAt = new Date().toISOString();
      const bodyJson = JSON.stringify(input.payload);
      const signature = buildEnqueueSignature(db, {
        path: COMMIT_PATH,
        clientTxnId,
        bodyJson,
        signedAt,
      });

      return enqueueTransaction(db, {
        endpoint: input.endpoint,
        payload: input.payload,
        signed_at: signedAt,
        auth_mode: input.auth_mode,
        grant_id: input.grant_id,
        device_signature: signature,
        client_txn_id: clientTxnId,
      });
    },
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

  // ── sync ───────────────────────────────────────────────────
  ipcMain.handle("sync.pushNow", async () => drainQueue(db));

  ipcMain.handle("sync.pullNow", async (_e, entity?: "products" | "stock") =>
    pullCatalog(db, entity),
  );

  ipcMain.handle("sync.state", async () => {
    const online = isOnline();
    const stats = getQueueStats(db);
    return { online, ...stats };
  });

  // ── authz ──────────────────────────────────────────────────
  ipcMain.handle("authz.currentGrant", () => currentGrant(db));

  ipcMain.handle("authz.grantState", () => grantState(db));

  ipcMain.handle("authz.refreshGrant", async () => {
    const baseUrl = getBaseUrl();
    return refreshGrant(db, { baseUrl });
  });

  ipcMain.handle("authz.consumeOverrideCode", (_e, code: string) =>
    consumeOverrideCode(db, code),
  );

  ipcMain.handle("authz.capabilities", async () => {
    const baseUrl = getBaseUrl();
    const res = await fetch(`${baseUrl}/api/v1/pos/capabilities`);
    if (!res.ok) throw new Error(`capabilities fetch failed: HTTP ${res.status}`);
    return res.json();
  });

  // ── device registration (called by settings UI / first-launch wizard) ──
  ipcMain.handle(
    "authz.registerDevice",
    async (_e, terminalId: number) => {
      const jwt = getSetting(db, "jwt");
      if (!jwt) throw new Error("Not authenticated — log in before registering device");
      const baseUrl = getBaseUrl();
      return registerDevice(db, { baseUrl, jwt, terminalId });
    },
  );

  ipcMain.handle("authz.isDeviceRegistered", () => isDeviceRegistered(db));

  // ── updater ────────────────────────────────────────────────
  ipcMain.handle("updater.isReady", () => {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { isUpdateReady } = require("../updater/index") as typeof import("../updater/index");
    return { ready: isUpdateReady() };
  });

  ipcMain.handle("updater.canInstall", async () => {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { canInstallUpdate } = require("../updater/index") as typeof import("../updater/index");
    const baseUrl = getBaseUrl();
    const minCompat = getSetting(db, "min_compatible_app_version") ?? "0.0.0";
    const schemaVer = Number(getSetting(db, "schema_version") ?? "1");
    return canInstallUpdate({
      baseUrl,
      localMinCompatibleAppVersion: minCompat,
      localSchemaVersion: schemaVer,
    });
  });

  ipcMain.handle("updater.quitAndInstall", async () => {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { isUpdateReady, canInstallUpdate, quitAndInstall } = require("../updater/index") as typeof import("../updater/index");
    if (!isUpdateReady()) throw new Error("No update downloaded yet");

    // Gate: block if the sync queue is not fully drained.
    const stats = getQueueStats(db);
    const unresolved = stats.pending + stats.syncing + stats.rejected;
    if (unresolved > 0) {
      throw new Error(`Cannot install update: ${unresolved} queue items unresolved. Drain queue first.`);
    }

    // Gate: block if the server has moved to a newer schema than the app can handle.
    const baseUrl = getBaseUrl();
    const minCompat = getSetting(db, "min_compatible_app_version") ?? "0.0.0";
    const schemaVer = Number(getSetting(db, "schema_version") ?? "1");
    const gate = await canInstallUpdate({
      baseUrl,
      localMinCompatibleAppVersion: minCompat,
      localSchemaVersion: schemaVer,
    });
    if (!gate.canInstall) {
      throw new Error(`Cannot install update: ${gate.reason}`);
    }

    quitAndInstall();
  });
}
