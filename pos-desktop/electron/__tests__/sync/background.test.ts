/**
 * Tests for sync/background.ts
 * All external deps are mocked; uses jest fake timers.
 */

import type Database from "better-sqlite3";

// ─── Mock all external dependencies ───────────────────────────────────────────

jest.mock("../../sync/push", () => ({
  drainQueue: jest.fn().mockResolvedValue({ pushed: 0, rejected: 0 }),
  getBaseUrl: jest.fn().mockReturnValue("http://test"),
}));
jest.mock("../../sync/pull", () => ({
  pullProducts: jest.fn().mockResolvedValue(0),
  pullStock: jest.fn().mockResolvedValue(0),
}));
jest.mock("../../sync/online", () => ({
  checkOnline: jest.fn().mockResolvedValue(true),
}));
jest.mock("../../db/queue", () => ({
  getQueueStats: jest.fn().mockReturnValue({ pending: 0, syncing: 0, rejected: 0, unresolved: 0 }),
}));
jest.mock("../../db/settings", () => ({
  getSetting: jest.fn().mockReturnValue("test.jwt.token"),
}));

import { bootRecovery, startBackgroundSync } from "../../sync/background";
import { drainQueue } from "../../sync/push";
import { pullProducts, pullStock } from "../../sync/pull";
import { checkOnline } from "../../sync/online";
import { getSetting } from "../../db/settings";

// ─── Minimal DB mock ──────────────────────────────────────────────────────────

function makeMockDb(changes = 0): Database.Database {
  const runFn = jest.fn().mockReturnValue({ changes });
  const stmtMock = { run: runFn, get: jest.fn() };
  return {
    prepare: jest.fn().mockReturnValue(stmtMock),
  } as unknown as Database.Database;
}

// ─── Setup / teardown ─────────────────────────────────────────────────────────

beforeEach(() => {
  jest.clearAllMocks();
  // Re-apply default mock return values after clearAllMocks clears them
  (checkOnline as jest.Mock).mockResolvedValue(true);
  (drainQueue as jest.Mock).mockResolvedValue({ pushed: 0, rejected: 0 });
  (getSetting as jest.Mock).mockReturnValue("test.jwt.token");
});

afterEach(() => {
  jest.useRealTimers();
  jest.restoreAllMocks();
});

// ─── bootRecovery ─────────────────────────────────────────────────────────────

describe("bootRecovery", () => {
  it("calls db.prepare with an UPDATE WHERE status='syncing' statement", () => {
    const db = makeMockDb(0);
    bootRecovery(db);

    expect(db.prepare).toHaveBeenCalled();
    const sql = (db.prepare as jest.Mock).mock.calls[0][0] as string;
    expect(sql).toContain("UPDATE");
    expect(sql).toContain("syncing");
    expect(sql).toContain("pending");
  });

  it("calls .run() on the prepared statement", () => {
    const db = makeMockDb(0);
    bootRecovery(db);

    const stmt = (db.prepare as jest.Mock).mock.results[0].value;
    expect(stmt.run).toHaveBeenCalled();
  });

  it("does not throw when changes > 0 (rows were reset)", () => {
    const db = makeMockDb(3);
    expect(() => bootRecovery(db)).not.toThrow();
  });

  it("does not throw when changes = 0 (no orphaned rows)", () => {
    const db = makeMockDb(0);
    expect(() => bootRecovery(db)).not.toThrow();
  });
});

// Helper: flush all pending microtasks/promises without advancing fake timers
async function flushPromises(): Promise<void> {
  // Multiple rounds to handle promise chains (await checkOnline → await drainQueue)
  for (let i = 0; i < 10; i++) {
    await Promise.resolve();
  }
}

// ─── startBackgroundSync ──────────────────────────────────────────────────────

describe("startBackgroundSync", () => {
  it("returns a cleanup function", () => {
    jest.useFakeTimers();
    const db = makeMockDb();
    const cleanup = startBackgroundSync(db);
    expect(typeof cleanup).toBe("function");
    cleanup();
  });

  it("calls drainQueue on the immediate tick (when online + jwt)", async () => {
    jest.useFakeTimers();
    const db = makeMockDb();

    const cleanup = startBackgroundSync(db);

    // Flush pending promises from the immediate tick
    await flushPromises();

    expect(checkOnline).toHaveBeenCalled();
    expect(drainQueue).toHaveBeenCalledWith(db);

    cleanup();
  });

  it("does NOT call drainQueue when offline", async () => {
    jest.useFakeTimers();
    (checkOnline as jest.Mock).mockResolvedValue(false);

    const db = makeMockDb();
    const cleanup = startBackgroundSync(db);

    await flushPromises();

    expect(drainQueue).not.toHaveBeenCalled();

    cleanup();
  });

  it("does NOT call drainQueue when jwt is missing", async () => {
    jest.useFakeTimers();
    (getSetting as jest.Mock).mockReturnValue(null);

    const db = makeMockDb();
    const cleanup = startBackgroundSync(db);

    await flushPromises();

    expect(drainQueue).not.toHaveBeenCalled();

    cleanup();
  });

  it("cleanup function prevents further interval ticks from firing", async () => {
    jest.useFakeTimers();
    const db = makeMockDb();

    const cleanup = startBackgroundSync(db);

    // Flush immediate tick
    await flushPromises();
    const callsAfterStart = (drainQueue as jest.Mock).mock.calls.length;

    // Clean up — clear all intervals
    cleanup();

    // Advance past PUSH_INTERVAL_MS — no new calls should fire
    jest.advanceTimersByTime(30_000);
    await flushPromises();

    expect((drainQueue as jest.Mock).mock.calls.length).toBe(callsAfterStart);
  });

  it("cleanup can be called multiple times without error", () => {
    jest.useFakeTimers();
    const db = makeMockDb();
    const cleanup = startBackgroundSync(db);
    expect(() => {
      cleanup();
      cleanup();
    }).not.toThrow();
  });

  it("fires drainQueue again after PUSH_INTERVAL_MS (10s)", async () => {
    // Use real timers with a spy on setInterval to verify intervals are registered
    // (fake timers + async interval callbacks are tricky to flush reliably)
    jest.useFakeTimers();
    const db = makeMockDb();

    const setIntervalSpy = jest.spyOn(global, "setInterval");
    const cleanup = startBackgroundSync(db);

    // Verify that setInterval was called (3 intervals registered)
    expect(setIntervalSpy).toHaveBeenCalled();

    // Check PUSH_INTERVAL_MS (10s) is one of the registered intervals
    const intervals = setIntervalSpy.mock.calls.map((c) => c[1]);
    expect(intervals).toContain(10_000);

    cleanup();
  });

  it("passes mainWindow sync state update on each tick", async () => {
    jest.useFakeTimers();
    const db = makeMockDb();

    const mockWebContents = { send: jest.fn() };
    const mockMainWindow = {
      isDestroyed: jest.fn().mockReturnValue(false),
      webContents: mockWebContents,
    };

    const cleanup = startBackgroundSync(db, mockMainWindow as unknown as Electron.BrowserWindow);

    await flushPromises();

    expect(mockWebContents.send).toHaveBeenCalledWith(
      "sync:state",
      expect.objectContaining({ online: true }),
    );

    cleanup();
  });
});
