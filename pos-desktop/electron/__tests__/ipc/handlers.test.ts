/**
 * Tests for registerIpcHandlers() in electron/ipc/handlers.ts.
 *
 * Strategy: mock `electron` to capture ipcMain.handle() callbacks into a
 * `handlers` map keyed by channel name. Mock every delegated module so we
 * can assert wiring and exercise the non-trivial logic (enqueue signature,
 * updater install gates, registerDevice auth guard, capabilities fetch).
 */

import type Database from "better-sqlite3";

// ─── capture registered handlers ────────────────────────────────────────────
type Handler = (...args: unknown[]) => unknown;
const handlers: Record<string, Handler> = {};

jest.mock("electron", () => ({
  ipcMain: {
    handle: (channel: string, fn: Handler) => {
      handlers[channel] = fn;
    },
  },
  app: {
    getVersion: jest.fn().mockReturnValue("1.2.3"),
    getPath: jest.fn().mockReturnValue("/tmp/logs"),
  },
}));

// ─── mock node:crypto.randomUUID for deterministic assertion ────────────────
jest.mock("node:crypto", () => ({
  ...jest.requireActual("node:crypto"),
  randomUUID: jest.fn().mockReturnValue("00000000-0000-0000-0000-000000000001"),
}));

// ─── mock delegated DB modules ──────────────────────────────────────────────
jest.mock("../../db/products", () => ({
  searchProducts: jest.fn(),
  getProductByCode: jest.fn(),
}));
jest.mock("../../db/stock", () => ({
  getStockForDrug: jest.fn(),
}));
jest.mock("../../db/queue", () => ({
  enqueueTransaction: jest.fn(),
  getPendingQueue: jest.fn(),
  getRejectedQueue: jest.fn(),
  getQueueStats: jest.fn(),
  reconcileTransaction: jest.fn(),
}));
jest.mock("../../db/shifts", () => ({
  getCurrentShift: jest.fn(),
  openShift: jest.fn(),
  closeShift: jest.fn(),
}));
jest.mock("../../db/settings", () => ({
  getSetting: jest.fn(),
  setSetting: jest.fn(),
}));
jest.mock("../../sync/push", () => ({
  drainQueue: jest.fn(),
  buildEnqueueSignature: jest.fn(),
  getBaseUrl: jest.fn(),
}));
jest.mock("../../sync/pull", () => ({
  pullCatalog: jest.fn(),
}));
jest.mock("../../sync/online", () => ({
  isOnline: jest.fn(),
}));
jest.mock("../../authz/device", () => ({
  isDeviceRegistered: jest.fn(),
  registerDevice: jest.fn(),
}));
jest.mock("../../authz/grants", () => ({
  currentGrant: jest.fn(),
  grantState: jest.fn(),
  consumeOverrideCode: jest.fn(),
  refreshGrant: jest.fn(),
}));
jest.mock("../../updater/index", () => ({
  isUpdateReady: jest.fn(),
  canInstallUpdate: jest.fn(),
  quitAndInstall: jest.fn(),
}));

// ─── import after mocks are set ─────────────────────────────────────────────
import { registerIpcHandlers } from "../../ipc/handlers";
import * as products from "../../db/products";
import * as stock from "../../db/stock";
import * as queue from "../../db/queue";
import * as shifts from "../../db/shifts";
import * as settings from "../../db/settings";
import * as push from "../../sync/push";
import * as pull from "../../sync/pull";
import * as online from "../../sync/online";
import * as device from "../../authz/device";
import * as grants from "../../authz/grants";
import * as updater from "../../updater/index";
import { app } from "electron";

const mockDb = { __marker: "db" } as unknown as Database.Database;
const mockHw = {
  printer: {
    print: jest.fn(),
    status: jest.fn(),
    testPrint: jest.fn(),
  },
  drawer: { open: jest.fn() },
  scanner: {} as unknown as never,
  mode: "mock" as const,
} as unknown as import("../../hardware/index").HardwareBundle;

beforeEach(() => {
  for (const k of Object.keys(handlers)) delete handlers[k];
  jest.clearAllMocks();
  registerIpcHandlers(mockDb, mockHw);
});

// ─── db.products ────────────────────────────────────────────────────────────
describe("db.products channels", () => {
  test("db.products.search delegates to searchProducts(db, q, limit)", async () => {
    (products.searchProducts as jest.Mock).mockReturnValue([{ drug_code: "X" }]);
    const res = await handlers["db.products.search"]({}, "foo", 20);
    expect(products.searchProducts).toHaveBeenCalledWith(mockDb, "foo", 20);
    expect(res).toEqual([{ drug_code: "X" }]);
  });

  test("db.products.byCode delegates to getProductByCode(db, code)", async () => {
    (products.getProductByCode as jest.Mock).mockReturnValue({ drug_code: "ABC" });
    const res = await handlers["db.products.byCode"]({}, "ABC");
    expect(products.getProductByCode).toHaveBeenCalledWith(mockDb, "ABC");
    expect(res).toEqual({ drug_code: "ABC" });
  });
});

// ─── db.stock ───────────────────────────────────────────────────────────────
describe("db.stock channels", () => {
  test("db.stock.forDrug delegates with drug + site", async () => {
    (stock.getStockForDrug as jest.Mock).mockReturnValue([{ qty: 5 }]);
    const res = await handlers["db.stock.forDrug"]({}, "DRG1", "S1");
    expect(stock.getStockForDrug).toHaveBeenCalledWith(mockDb, "DRG1", "S1");
    expect(res).toEqual([{ qty: 5 }]);
  });
});

// ─── db.queue ───────────────────────────────────────────────────────────────
describe("db.queue channels", () => {
  test("db.queue.enqueue generates UUID, builds signature, enqueues", async () => {
    (push.buildEnqueueSignature as jest.Mock).mockReturnValue("SIG123");
    (queue.enqueueTransaction as jest.Mock).mockReturnValue({ local_id: "L1" });

    const payload = { lines: [{ drug: "X" }] };
    const input = {
      endpoint: "/api/v1/pos/transactions/commit",
      payload,
      auth_mode: "bearer" as const,
      grant_id: null,
    };
    const res = await handlers["db.queue.enqueue"]({}, input);

    // buildEnqueueSignature called with deterministic UUID + COMMIT_PATH
    expect(push.buildEnqueueSignature).toHaveBeenCalledTimes(1);
    const sigArgs = (push.buildEnqueueSignature as jest.Mock).mock.calls[0];
    expect(sigArgs[0]).toBe(mockDb);
    expect(sigArgs[1]).toMatchObject({
      path: "/api/v1/pos/transactions/commit",
      clientTxnId: "00000000-0000-0000-0000-000000000001",
      bodyJson: JSON.stringify(payload),
    });
    expect(typeof sigArgs[1].signedAt).toBe("string");

    // enqueueTransaction called with the signature
    expect(queue.enqueueTransaction).toHaveBeenCalledTimes(1);
    const enqArgs = (queue.enqueueTransaction as jest.Mock).mock.calls[0];
    expect(enqArgs[0]).toBe(mockDb);
    expect(enqArgs[1]).toMatchObject({
      endpoint: input.endpoint,
      payload,
      auth_mode: "bearer",
      grant_id: null,
      device_signature: "SIG123",
      client_txn_id: "00000000-0000-0000-0000-000000000001",
    });

    expect(res).toEqual({ local_id: "L1" });
  });

  test("db.queue.pending delegates", async () => {
    (queue.getPendingQueue as jest.Mock).mockReturnValue([{ id: 1 }]);
    const res = await handlers["db.queue.pending"]({});
    expect(queue.getPendingQueue).toHaveBeenCalledWith(mockDb);
    expect(res).toEqual([{ id: 1 }]);
  });

  test("db.queue.rejected delegates", async () => {
    (queue.getRejectedQueue as jest.Mock).mockReturnValue([{ id: 2 }]);
    const res = await handlers["db.queue.rejected"]({});
    expect(queue.getRejectedQueue).toHaveBeenCalledWith(mockDb);
    expect(res).toEqual([{ id: 2 }]);
  });

  test("db.queue.stats delegates", async () => {
    (queue.getQueueStats as jest.Mock).mockReturnValue({ pending: 0, syncing: 0, rejected: 0 });
    const res = await handlers["db.queue.stats"]({});
    expect(queue.getQueueStats).toHaveBeenCalledWith(mockDb);
    expect(res).toEqual({ pending: 0, syncing: 0, rejected: 0 });
  });

  test("db.queue.reconcile delegates all 4 args", async () => {
    (queue.reconcileTransaction as jest.Mock).mockReturnValue({ ok: true });
    const res = await handlers["db.queue.reconcile"](
      {},
      "L1",
      "retry_override",
      "manager approved",
      "OVR-1",
    );
    expect(queue.reconcileTransaction).toHaveBeenCalledWith(
      mockDb,
      "L1",
      "retry_override",
      "manager approved",
      "OVR-1",
    );
    expect(res).toEqual({ ok: true });
  });
});

// ─── db.shifts ──────────────────────────────────────────────────────────────
describe("db.shifts channels", () => {
  test("db.shifts.current delegates", async () => {
    (shifts.getCurrentShift as jest.Mock).mockReturnValue({ shift_id: "S1" });
    const res = await handlers["db.shifts.current"]({});
    expect(shifts.getCurrentShift).toHaveBeenCalledWith(mockDb);
    expect(res).toEqual({ shift_id: "S1" });
  });

  test("db.shifts.open delegates payload", async () => {
    (shifts.openShift as jest.Mock).mockReturnValue({ shift_id: "S2" });
    const payload = { opened_by: "u1", opening_cash: 100 } as unknown as Parameters<
      typeof shifts.openShift
    >[1];
    const res = await handlers["db.shifts.open"]({}, payload);
    expect(shifts.openShift).toHaveBeenCalledWith(mockDb, payload);
    expect(res).toEqual({ shift_id: "S2" });
  });

  test("db.shifts.close delegates payload", async () => {
    (shifts.closeShift as jest.Mock).mockReturnValue({ shift_id: "S2", closed: true });
    const payload = { shift_id: "S2", closing_cash: 200 } as unknown as Parameters<
      typeof shifts.closeShift
    >[1];
    const res = await handlers["db.shifts.close"]({}, payload);
    expect(shifts.closeShift).toHaveBeenCalledWith(mockDb, payload);
    expect(res).toEqual({ shift_id: "S2", closed: true });
  });
});

// ─── db.settings ────────────────────────────────────────────────────────────
describe("db.settings channels", () => {
  test("db.settings.get delegates", async () => {
    (settings.getSetting as jest.Mock).mockReturnValue("value");
    const res = await handlers["db.settings.get"]({}, "key1");
    expect(settings.getSetting).toHaveBeenCalledWith(mockDb, "key1");
    expect(res).toBe("value");
  });

  test("db.settings.set delegates and returns undefined", async () => {
    const res = await handlers["db.settings.set"]({}, "key1", "val1");
    expect(settings.setSetting).toHaveBeenCalledWith(mockDb, "key1", "val1");
    expect(res).toBeUndefined();
  });
});

// ─── printer / drawer ───────────────────────────────────────────────────────
describe("printer + drawer channels", () => {
  test("printer.print delegates to hw.printer.print", async () => {
    (mockHw.printer.print as jest.Mock).mockResolvedValue({ success: true });
    const payload = { lines: ["a", "b"] };
    const res = await handlers["printer.print"]({}, payload);
    expect(mockHw.printer.print).toHaveBeenCalledWith(payload);
    expect(res).toEqual({ success: true });
  });

  test("printer.status delegates", async () => {
    (mockHw.printer.status as jest.Mock).mockResolvedValue({ online: true });
    const res = await handlers["printer.status"]({});
    expect(mockHw.printer.status).toHaveBeenCalled();
    expect(res).toEqual({ online: true });
  });

  test("printer.testPrint delegates", async () => {
    (mockHw.printer.testPrint as jest.Mock).mockResolvedValue({ success: true });
    const res = await handlers["printer.testPrint"]({});
    expect(mockHw.printer.testPrint).toHaveBeenCalled();
    expect(res).toEqual({ success: true });
  });

  test("drawer.open delegates", async () => {
    (mockHw.drawer.open as jest.Mock).mockResolvedValue({ success: true });
    const res = await handlers["drawer.open"]({});
    expect(mockHw.drawer.open).toHaveBeenCalled();
    expect(res).toEqual({ success: true });
  });
});

// ─── app ────────────────────────────────────────────────────────────────────
describe("app channels", () => {
  test("app.version calls app.getVersion()", async () => {
    const res = await handlers["app.version"]({});
    expect(app.getVersion).toHaveBeenCalled();
    expect(res).toBe("1.2.3");
  });

  test("app.logsPath calls app.getPath('logs')", async () => {
    const res = await handlers["app.logsPath"]({});
    expect(app.getPath).toHaveBeenCalledWith("logs");
    expect(res).toBe("/tmp/logs");
  });
});

// ─── sync ───────────────────────────────────────────────────────────────────
describe("sync channels", () => {
  test("sync.pushNow delegates to drainQueue(db)", async () => {
    (push.drainQueue as jest.Mock).mockResolvedValue({ drained: 2 });
    const res = await handlers["sync.pushNow"]({});
    expect(push.drainQueue).toHaveBeenCalledWith(mockDb);
    expect(res).toEqual({ drained: 2 });
  });

  test("sync.pullNow delegates entity arg", async () => {
    (pull.pullCatalog as jest.Mock).mockResolvedValue({ pulled: 10 });
    const res = await handlers["sync.pullNow"]({}, "products");
    expect(pull.pullCatalog).toHaveBeenCalledWith(mockDb, "products");
    expect(res).toEqual({ pulled: 10 });
  });

  test("sync.state merges online + queue stats", async () => {
    (online.isOnline as jest.Mock).mockReturnValue(true);
    (queue.getQueueStats as jest.Mock).mockReturnValue({
      pending: 1,
      syncing: 0,
      rejected: 2,
    });
    const res = await handlers["sync.state"]({});
    expect(online.isOnline).toHaveBeenCalled();
    expect(queue.getQueueStats).toHaveBeenCalledWith(mockDb);
    expect(res).toEqual({ online: true, pending: 1, syncing: 0, rejected: 2 });
  });
});

// ─── authz ──────────────────────────────────────────────────────────────────
describe("authz channels", () => {
  test("authz.currentGrant delegates", async () => {
    (grants.currentGrant as jest.Mock).mockReturnValue({ id: "g1" });
    const res = await handlers["authz.currentGrant"]({});
    expect(grants.currentGrant).toHaveBeenCalledWith(mockDb);
    expect(res).toEqual({ id: "g1" });
  });

  test("authz.grantState delegates", async () => {
    (grants.grantState as jest.Mock).mockReturnValue("active");
    const res = await handlers["authz.grantState"]({});
    expect(grants.grantState).toHaveBeenCalledWith(mockDb);
    expect(res).toBe("active");
  });

  test("authz.consumeOverrideCode delegates code", async () => {
    (grants.consumeOverrideCode as jest.Mock).mockReturnValue({ ok: true });
    const res = await handlers["authz.consumeOverrideCode"]({}, "OVR-123");
    expect(grants.consumeOverrideCode).toHaveBeenCalledWith(mockDb, "OVR-123");
    expect(res).toEqual({ ok: true });
  });

  test("authz.refreshGrant calls refreshGrant(db, { baseUrl })", async () => {
    (push.getBaseUrl as jest.Mock).mockReturnValue("https://api.example.com");
    (grants.refreshGrant as jest.Mock).mockResolvedValue({ refreshed: true });
    const res = await handlers["authz.refreshGrant"]({});
    expect(push.getBaseUrl).toHaveBeenCalled();
    expect(grants.refreshGrant).toHaveBeenCalledWith(mockDb, {
      baseUrl: "https://api.example.com",
    });
    expect(res).toEqual({ refreshed: true });
  });

  describe("authz.capabilities", () => {
    const originalFetch = global.fetch;
    afterEach(() => {
      global.fetch = originalFetch;
    });

    test("fetches capabilities and returns json on ok", async () => {
      (push.getBaseUrl as jest.Mock).mockReturnValue("https://api.example.com");
      const jsonFn = jest.fn().mockResolvedValue({ features: ["a"] });
      global.fetch = jest.fn().mockResolvedValue({ ok: true, json: jsonFn }) as unknown as typeof fetch;
      const res = await handlers["authz.capabilities"]({});
      expect(global.fetch).toHaveBeenCalledWith(
        "https://api.example.com/api/v1/pos/capabilities",
      );
      expect(res).toEqual({ features: ["a"] });
    });

    test("throws on non-ok response", async () => {
      (push.getBaseUrl as jest.Mock).mockReturnValue("https://api.example.com");
      global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 503 }) as unknown as typeof fetch;
      await expect(handlers["authz.capabilities"]({})).rejects.toThrow(
        /capabilities fetch failed: HTTP 503/,
      );
    });
  });

  describe("authz.registerDevice", () => {
    test("throws 'Not authenticated' when jwt setting is missing", async () => {
      (settings.getSetting as jest.Mock).mockReturnValue(null);
      await expect(handlers["authz.registerDevice"]({}, 7)).rejects.toThrow(
        /Not authenticated/,
      );
      expect(device.registerDevice).not.toHaveBeenCalled();
    });

    test("calls registerDevice(db, { baseUrl, jwt, terminalId }) when jwt present", async () => {
      (settings.getSetting as jest.Mock).mockReturnValue("jwt-token");
      (push.getBaseUrl as jest.Mock).mockReturnValue("https://api.example.com");
      (device.registerDevice as jest.Mock).mockResolvedValue({ registered: true });
      const res = await handlers["authz.registerDevice"]({}, 7);
      expect(device.registerDevice).toHaveBeenCalledWith(mockDb, {
        baseUrl: "https://api.example.com",
        jwt: "jwt-token",
        terminalId: 7,
      });
      expect(res).toEqual({ registered: true });
    });
  });

  test("authz.isDeviceRegistered delegates", async () => {
    (device.isDeviceRegistered as jest.Mock).mockReturnValue(true);
    const res = await handlers["authz.isDeviceRegistered"]({});
    expect(device.isDeviceRegistered).toHaveBeenCalledWith(mockDb);
    expect(res).toBe(true);
  });
});

// ─── updater ────────────────────────────────────────────────────────────────
describe("updater channels", () => {
  test("updater.isReady returns { ready: bool }", async () => {
    (updater.isUpdateReady as jest.Mock).mockReturnValue(true);
    const res = await handlers["updater.isReady"]({});
    expect(updater.isUpdateReady).toHaveBeenCalled();
    expect(res).toEqual({ ready: true });
  });

  test("updater.canInstall reads settings and calls canInstallUpdate", async () => {
    (push.getBaseUrl as jest.Mock).mockReturnValue("https://api.example.com");
    (settings.getSetting as jest.Mock).mockImplementation((_db, k: string) => {
      if (k === "jwt") return "jwt-1";
      if (k === "min_compatible_app_version") return "1.0.0";
      if (k === "schema_version") return "3";
      return null;
    });
    (updater.canInstallUpdate as jest.Mock).mockResolvedValue({ canInstall: true });
    const res = await handlers["updater.canInstall"]({});
    expect(updater.canInstallUpdate).toHaveBeenCalledWith({
      baseUrl: "https://api.example.com",
      jwt: "jwt-1",
      currentVersion: "1.2.3",
      channel: "stable",
      platform: process.platform,
      localMinCompatibleAppVersion: "1.0.0",
      localSchemaVersion: 3,
    });
    expect(res).toEqual({ canInstall: true });
  });

  test("updater.canInstall uses defaults when settings missing", async () => {
    (push.getBaseUrl as jest.Mock).mockReturnValue("https://api.example.com");
    (settings.getSetting as jest.Mock).mockReturnValue(null);
    (updater.canInstallUpdate as jest.Mock).mockResolvedValue({ canInstall: true });
    await handlers["updater.canInstall"]({});
    expect(updater.canInstallUpdate).toHaveBeenCalledWith({
      baseUrl: "https://api.example.com",
      jwt: null,
      currentVersion: "1.2.3",
      channel: "stable",
      platform: process.platform,
      localMinCompatibleAppVersion: "0.0.0",
      localSchemaVersion: 1,
    });
  });

  describe("updater.quitAndInstall gates", () => {
    test("throws 'No update downloaded yet' when isUpdateReady=false", async () => {
      (updater.isUpdateReady as jest.Mock).mockReturnValue(false);
      await expect(handlers["updater.quitAndInstall"]({})).rejects.toThrow(
        /No update downloaded yet/,
      );
      expect(updater.quitAndInstall).not.toHaveBeenCalled();
    });

    test("throws when queue items unresolved (pending > 0)", async () => {
      (updater.isUpdateReady as jest.Mock).mockReturnValue(true);
      (queue.getQueueStats as jest.Mock).mockReturnValue({
        pending: 1,
        syncing: 0,
        rejected: 0,
      });
      await expect(handlers["updater.quitAndInstall"]({})).rejects.toThrow(
        /1 queue items unresolved/,
      );
      expect(updater.quitAndInstall).not.toHaveBeenCalled();
    });

    test("throws when syncing or rejected > 0", async () => {
      (updater.isUpdateReady as jest.Mock).mockReturnValue(true);
      (queue.getQueueStats as jest.Mock).mockReturnValue({
        pending: 0,
        syncing: 2,
        rejected: 3,
      });
      await expect(handlers["updater.quitAndInstall"]({})).rejects.toThrow(
        /5 queue items unresolved/,
      );
    });

    test("throws with gate.reason when canInstallUpdate returns canInstall=false", async () => {
      (updater.isUpdateReady as jest.Mock).mockReturnValue(true);
      (queue.getQueueStats as jest.Mock).mockReturnValue({
        pending: 0,
        syncing: 0,
        rejected: 0,
      });
      (push.getBaseUrl as jest.Mock).mockReturnValue("https://api.example.com");
      (settings.getSetting as jest.Mock).mockReturnValue(null);
      (updater.canInstallUpdate as jest.Mock).mockResolvedValue({
        canInstall: false,
        reason: "schema_too_old",
      });
      await expect(handlers["updater.quitAndInstall"]({})).rejects.toThrow(
        /schema_too_old/,
      );
      expect(updater.quitAndInstall).not.toHaveBeenCalled();
    });

    test("calls quitAndInstall() on happy path (all gates pass)", async () => {
      (updater.isUpdateReady as jest.Mock).mockReturnValue(true);
      (queue.getQueueStats as jest.Mock).mockReturnValue({
        pending: 0,
        syncing: 0,
        rejected: 0,
      });
      (push.getBaseUrl as jest.Mock).mockReturnValue("https://api.example.com");
      (settings.getSetting as jest.Mock).mockImplementation((_db, k: string) => {
        if (k === "jwt") return "jwt-1";
        if (k === "min_compatible_app_version") return "1.0.0";
        if (k === "schema_version") return "2";
        return null;
      });
      (updater.canInstallUpdate as jest.Mock).mockResolvedValue({ canInstall: true });

      await handlers["updater.quitAndInstall"]({});

      expect(updater.canInstallUpdate).toHaveBeenCalledWith({
        baseUrl: "https://api.example.com",
        jwt: "jwt-1",
        currentVersion: "1.2.3",
        channel: "stable",
        platform: process.platform,
        localMinCompatibleAppVersion: "1.0.0",
        localSchemaVersion: 2,
      });
      expect(updater.quitAndInstall).toHaveBeenCalledTimes(1);
    });
  });
});

// ─── sanity: all expected channels are registered ──────────────────────────
describe("channel coverage", () => {
  test("all expected channels registered", () => {
    const expected = [
      "db.products.search",
      "db.products.byCode",
      "db.stock.forDrug",
      "db.queue.enqueue",
      "db.queue.pending",
      "db.queue.rejected",
      "db.queue.stats",
      "db.queue.reconcile",
      "db.shifts.current",
      "db.shifts.open",
      "db.shifts.close",
      "db.settings.get",
      "db.settings.set",
      "printer.print",
      "printer.status",
      "printer.testPrint",
      "drawer.open",
      "app.version",
      "app.logsPath",
      "sync.pushNow",
      "sync.pullNow",
      "sync.state",
      "authz.currentGrant",
      "authz.grantState",
      "authz.refreshGrant",
      "authz.consumeOverrideCode",
      "authz.capabilities",
      "authz.registerDevice",
      "authz.isDeviceRegistered",
      "updater.isReady",
      "updater.canInstall",
      "updater.quitAndInstall",
    ];
    for (const ch of expected) {
      expect(handlers[ch]).toBeDefined();
    }
  });
});
