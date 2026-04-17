/**
 * offline-db adapter tests — verifies the IPC path is used when Electron
 * is present and the HTTP path otherwise. Uses Vitest module mocks for
 * both `ipc` and `api-client`.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/pos/ipc", () => ({
  hasElectron: vi.fn(),
  db: {
    products: {
      search: vi.fn(),
      byCode: vi.fn(),
    },
    queue: {
      stats: vi.fn(),
    },
  },
}));

vi.mock("@/lib/api-client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api-client")>("@/lib/api-client");
  return {
    ...actual,
    fetchAPI: vi.fn(),
  };
});

import { ApiError, fetchAPI } from "@/lib/api-client";
import * as ipc from "@/lib/pos/ipc";
import { getProductByCode, getQueueStats, searchProducts } from "@/lib/pos/offline-db";

// The `vi.mock` factories above return `vi.fn()` for each nested helper,
// but the compile-time type of `ipc.db.products.search` is still the real
// function signature. Cast once to the vi.Mock type so `.mockResolvedValue`
// and friends type-check.
const hasElectronMock = ipc.hasElectron as unknown as ReturnType<typeof vi.fn>;
const searchMock = ipc.db.products.search as unknown as ReturnType<typeof vi.fn>;
const byCodeMock = ipc.db.products.byCode as unknown as ReturnType<typeof vi.fn>;
const statsMock = ipc.db.queue.stats as unknown as ReturnType<typeof vi.fn>;
const fetchAPIMock = fetchAPI as unknown as ReturnType<typeof vi.fn>;

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.resetAllMocks();
});

describe("searchProducts", () => {
  it("uses IPC when Electron is present", async () => {
    hasElectronMock.mockReturnValue(true);
    searchMock.mockResolvedValue([
      {
        drug_code: "D1",
        drug_name: "Paracetamol",
        drug_brand: null,
        drug_cluster: null,
        is_controlled: false,
        requires_pharmacist: false,
        unit_price: "12.00",
        updated_at: "2026-04-17T06:00:00Z",
      },
    ]);

    const out = await searchProducts("para", 10);
    expect(searchMock).toHaveBeenCalledWith("para", 10);
    expect(fetchAPIMock).not.toHaveBeenCalled();
    expect(out[0].drug_code).toBe("D1");
  });

  it("falls back to HTTP when Electron is absent", async () => {
    hasElectronMock.mockReturnValue(false);
    fetchAPIMock.mockResolvedValue([
      {
        drug_code: "D2",
        drug_name: "Amoxicillin",
        drug_brand: null,
        unit_price: "24.00",
        is_controlled: false,
        requires_pharmacist: false,
      },
    ]);

    const out = await searchProducts("amox");
    expect(fetchAPIMock).toHaveBeenCalledWith(
      expect.stringContaining("/pos/products/search?q=amox"),
    );
    expect(out[0].drug_code).toBe("D2");
  });
});

describe("getProductByCode", () => {
  it("returns null on HTTP 404", async () => {
    hasElectronMock.mockReturnValue(false);
    fetchAPIMock.mockRejectedValue(new ApiError(404, "not found"));
    const out = await getProductByCode("DOES-NOT-EXIST");
    expect(out).toBeNull();
  });

  it("rethrows non-404 HTTP errors", async () => {
    hasElectronMock.mockReturnValue(false);
    fetchAPIMock.mockRejectedValue(new ApiError(500, "boom"));
    await expect(getProductByCode("X")).rejects.toBeInstanceOf(ApiError);
  });

  it("returns null when IPC byCode returns null", async () => {
    hasElectronMock.mockReturnValue(true);
    byCodeMock.mockResolvedValue(null);
    const out = await getProductByCode("X");
    expect(out).toBeNull();
  });
});

describe("getQueueStats", () => {
  it("returns IPC stats under Electron", async () => {
    hasElectronMock.mockReturnValue(true);
    statsMock.mockResolvedValue({
      pending: 1,
      syncing: 0,
      rejected: 2,
      unresolved: 3,
      last_sync_at: "2026-04-17T09:00:00Z",
    });
    const s = await getQueueStats();
    expect(s.unresolved).toBe(3);
  });

  it("returns a zero snapshot in the browser", async () => {
    hasElectronMock.mockReturnValue(false);
    const s = await getQueueStats();
    expect(s).toEqual({
      pending: 0,
      syncing: 0,
      rejected: 0,
      unresolved: 0,
      last_sync_at: null,
    });
  });
});
