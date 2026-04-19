import { describe, it, expect } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import React from "react";
import { useVouchers, createVoucher } from "@/hooks/use-vouchers";

function wrapper({ children }: { children: React.ReactNode }) {
  return React.createElement(
    SWRConfig,
    { value: { dedupingInterval: 0, provider: () => new Map() } },
    children,
  );
}

describe("useVouchers", () => {
  it("fetches the tenant voucher list", async () => {
    const { result } = renderHook(() => useVouchers(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data).toHaveLength(2);
    expect(result.current.data[0].code).toBe("SUMMER25");
  });

  it("filters by status when supplied", async () => {
    const { result } = renderHook(() => useVouchers({ status: "redeemed" }), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data).toHaveLength(1);
    expect(result.current.data[0].code).toBe("FLAT50");
    expect(result.current.data[0].status).toBe("redeemed");
  });

  it("returns empty array before data resolves (no undefined)", () => {
    const { result } = renderHook(() => useVouchers(), { wrapper });
    // Initial render — data fallback is [] to keep callers branch-free
    expect(Array.isArray(result.current.data)).toBe(true);
  });
});

describe("createVoucher", () => {
  it("posts the payload and returns the server row", async () => {
    const result = await createVoucher({
      code: "NEWCODE",
      discount_type: "amount",
      value: 15,
      max_uses: 5,
    });
    expect(result.id).toBe(99);
    expect(result.code).toBe("NEWCODE");
    expect(result.status).toBe("active");
  });
});
