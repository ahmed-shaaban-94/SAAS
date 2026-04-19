/**
 * Tests for sync/pull.ts
 * All HTTP calls + DB helpers are mocked — no real DB or network.
 */

import type Database from "better-sqlite3";

// ─── Mock all external dependencies ───────────────────────────────────────────

jest.mock("../../db/products", () => ({
  upsertProducts: jest.fn(),
}));
jest.mock("../../db/stock", () => ({
  upsertStock: jest.fn(),
}));
jest.mock("../../db/settings", () => ({
  getSetting: jest.fn(),
}));
jest.mock("../../sync/push", () => ({
  getBaseUrl: jest.fn().mockReturnValue("http://test"),
  drainQueue: jest.fn(),
}));

import { pullProducts, pullStock, pullCatalog } from "../../sync/pull";
import { upsertProducts } from "../../db/products";
import { upsertStock } from "../../db/stock";
import { getSetting } from "../../db/settings";
import { getBaseUrl } from "../../sync/push";

// ─── Minimal DB mock ──────────────────────────────────────────────────────────

function makeMockDb(overrides?: {
  lastCursor?: string | null;
  runChanges?: number;
}): Database.Database {
  const runFn = jest.fn().mockReturnValue({ changes: overrides?.runChanges ?? 0 });
  const getFn = jest.fn().mockReturnValue(
    overrides?.lastCursor !== undefined
      ? { last_cursor: overrides.lastCursor }
      : undefined,
  );
  return {
    prepare: jest.fn().mockReturnValue({ run: runFn, get: getFn }),
  } as unknown as Database.Database;
}

// ─── Setup / teardown ─────────────────────────────────────────────────────────

beforeEach(() => {
  jest.clearAllMocks();
  // Default: JWT is set, baseUrl is http://test
  (getSetting as jest.Mock).mockReturnValue("test.jwt.token");
  (getBaseUrl as jest.Mock).mockReturnValue("http://test");
  global.fetch = jest.fn();
});

afterEach(() => {
  jest.restoreAllMocks();
});

// ─── pullProducts ─────────────────────────────────────────────────────────────

describe("pullProducts", () => {
  it("returns 0 when no jwt in settings", async () => {
    (getSetting as jest.Mock).mockReturnValue(null);
    const db = makeMockDb();
    const result = await pullProducts(db);
    expect(result).toBe(0);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("fetches one page, upserts items, saves null cursor, returns item count", async () => {
    const items = [
      {
        drug_code: "D001",
        drug_name: "Paracetamol",
        drug_brand: null,
        drug_cluster: null,
        is_controlled: false,
        requires_pharmacist: false,
        unit_price: "5.00",
        updated_at: "2026-01-01T00:00:00Z",
      },
      {
        drug_code: "D002",
        drug_name: "Ibuprofen",
        drug_brand: "Advil",
        drug_cluster: null,
        is_controlled: false,
        requires_pharmacist: false,
        unit_price: "8.00",
        updated_at: "2026-01-01T00:00:00Z",
      },
    ];

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ items, next_cursor: null }),
    });

    const db = makeMockDb();
    const result = await pullProducts(db);

    expect(result).toBe(2);
    expect(upsertProducts).toHaveBeenCalledTimes(1);
    expect(upsertProducts).toHaveBeenCalledWith(db, items);

    // Verify the null cursor reset was saved
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const runFn = (db.prepare as jest.Mock).mock.results
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .map((r: any) => r.value?.run as jest.Mock | undefined)
      .find(Boolean);
    expect(runFn).toBeDefined();
    const nullCursorCall = (runFn as jest.Mock).mock.calls.find(
      (args: unknown[]) => args[0] === null
    );
    expect(nullCursorCall).toBeDefined();
  });

  it("follows next_cursor across pages, resets cursor to null at end", async () => {
    const page1Items = [
      {
        drug_code: "D001",
        drug_name: "Paracetamol",
        drug_brand: null,
        drug_cluster: null,
        is_controlled: false,
        requires_pharmacist: false,
        unit_price: "5.00",
        updated_at: "2026-01-01T00:00:00Z",
      },
    ];
    const page2Items = [
      {
        drug_code: "D002",
        drug_name: "Ibuprofen",
        drug_brand: null,
        drug_cluster: null,
        is_controlled: false,
        requires_pharmacist: false,
        unit_price: "8.00",
        updated_at: "2026-01-01T00:00:00Z",
      },
    ];

    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ items: page1Items, next_cursor: "cursor-page-2" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ items: page2Items, next_cursor: null }),
      });

    const db = makeMockDb();
    const result = await pullProducts(db);

    expect(result).toBe(2);
    expect(global.fetch).toHaveBeenCalledTimes(2);
    expect(upsertProducts).toHaveBeenCalledTimes(2);

    // First fetch should not include cursor (no cursor initially)
    const firstUrl = (global.fetch as jest.Mock).mock.calls[0][0] as string;
    expect(firstUrl).not.toContain("cursor=");

    // Second fetch should include cursor
    const secondUrl = (global.fetch as jest.Mock).mock.calls[1][0] as string;
    expect(secondUrl).toContain("cursor=cursor-page-2");
  });

  it("throws when fetch returns non-ok response", async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 503,
      statusText: "Service Unavailable",
    });

    const db = makeMockDb();
    await expect(pullProducts(db)).rejects.toThrow("503");
  });

  it("uses Bearer JWT in Authorization header", async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ items: [], next_cursor: null }),
    });

    const db = makeMockDb();
    await pullProducts(db);

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/pos/catalog/products"),
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer test.jwt.token" }),
      }),
    );
  });
});

// ─── pullStock ────────────────────────────────────────────────────────────────

describe("pullStock", () => {
  it("returns 0 when no jwt", async () => {
    (getSetting as jest.Mock).mockReturnValue(null);
    const db = makeMockDb();
    const result = await pullStock(db);
    expect(result).toBe(0);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("URL has no ?site= param when site is not provided", async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ items: [], next_cursor: null }),
    });

    const db = makeMockDb();
    await pullStock(db);

    const url = (global.fetch as jest.Mock).mock.calls[0][0] as string;
    expect(url).not.toContain("site=");
  });

  it("URL includes ?site=X when site is provided", async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ items: [], next_cursor: null }),
    });

    const db = makeMockDb();
    await pullStock(db, "SITE-A");

    const url = (global.fetch as jest.Mock).mock.calls[0][0] as string;
    expect(url).toContain("site=SITE-A");
  });

  it("upserts stock items and returns total count", async () => {
    const items = [
      {
        drug_code: "D001",
        site_code: "SITE-A",
        batch_number: "B001",
        quantity: "100",
        expiry_date: "2027-12-31",
        updated_at: "2026-01-01T00:00:00Z",
      },
    ];

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ items, next_cursor: null }),
    });

    const db = makeMockDb();
    const result = await pullStock(db);

    expect(result).toBe(1);
    expect(upsertStock).toHaveBeenCalledTimes(1);
    expect(upsertStock).toHaveBeenCalledWith(
      db,
      expect.arrayContaining([
        expect.objectContaining({ drug_code: "D001", batch_number: "B001" }),
      ]),
    );
  });

  it("throws when fetch returns non-ok response", async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
    });

    const db = makeMockDb();
    await expect(pullStock(db)).rejects.toThrow("401");
  });
});

// ─── pullCatalog ──────────────────────────────────────────────────────────────

describe("pullCatalog", () => {
  it("calls both pullProducts and pullStock when entity is not specified", async () => {
    // Two calls: one for products, one for stock
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ items: [{ drug_code: "D001", drug_name: "X", drug_brand: null, drug_cluster: null, is_controlled: false, requires_pharmacist: false, unit_price: "1.00", updated_at: "2026-01-01T00:00:00Z" }], next_cursor: null }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ items: [], next_cursor: null }),
      });

    const db = makeMockDb();
    const result = await pullCatalog(db);

    expect(global.fetch).toHaveBeenCalledTimes(2);
    // First fetch is products
    expect((global.fetch as jest.Mock).mock.calls[0][0]).toContain("/catalog/products");
    // Second fetch is stock
    expect((global.fetch as jest.Mock).mock.calls[1][0]).toContain("/catalog/stock");
    expect(result.pulled).toBe(1); // 1 product + 0 stock
  });

  it("calls only products when entity='products'", async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ items: [], next_cursor: null }),
    });

    const db = makeMockDb();
    await pullCatalog(db, "products");

    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect((global.fetch as jest.Mock).mock.calls[0][0]).toContain("/catalog/products");
    expect((global.fetch as jest.Mock).mock.calls[0][0]).not.toContain("/catalog/stock");
  });

  it("calls only stock when entity='stock'", async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ items: [], next_cursor: null }),
    });

    const db = makeMockDb();
    await pullCatalog(db, "stock");

    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect((global.fetch as jest.Mock).mock.calls[0][0]).toContain("/catalog/stock");
    expect((global.fetch as jest.Mock).mock.calls[0][0]).not.toContain("/catalog/products");
  });

  it("returns {pulled: N} reflecting total rows across both entities", async () => {
    const products = Array.from({ length: 3 }, (_, i) => ({
      drug_code: `D00${i}`,
      drug_name: `Drug ${i}`,
      drug_brand: null,
      drug_cluster: null,
      is_controlled: false,
      requires_pharmacist: false,
      unit_price: "1.00",
      updated_at: "2026-01-01T00:00:00Z",
    }));
    const stockItems = Array.from({ length: 2 }, (_, i) => ({
      drug_code: `D00${i}`,
      site_code: "SITE-A",
      batch_number: `B00${i}`,
      quantity: "50",
      expiry_date: null,
      updated_at: "2026-01-01T00:00:00Z",
    }));

    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ items: products, next_cursor: null }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ items: stockItems, next_cursor: null }),
      });

    const db = makeMockDb();
    const result = await pullCatalog(db);

    expect(result.pulled).toBe(5); // 3 products + 2 stock
  });
});
