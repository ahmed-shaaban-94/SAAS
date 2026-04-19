import { describe, it, expect } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useVoucherValidate } from "@/hooks/use-voucher-validate";

describe("useVoucherValidate", () => {
  it("returns discount payload for an active percent voucher", async () => {
    const { result } = renderHook(() => useVoucherValidate());

    await act(async () => {
      await result.current.validate({ code: "SUMMER25" });
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data?.code).toBe("SUMMER25");
    expect(result.current.data?.discount_type).toBe("percent");
    expect(result.current.data?.value).toBe(25);
    expect(result.current.error).toBeNull();
    expect(result.current.errorKind).toBeNull();
  });

  it("forwards optional cart_subtotal to the server", async () => {
    const { result } = renderHook(() => useVoucherValidate());

    await act(async () => {
      await result.current.validate({ code: "FLAT50", cart_subtotal: 500 });
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data?.code).toBe("FLAT50");
    expect(result.current.data?.min_purchase).toBe(200);
  });

  it("classifies 404 as voucher_not_found", async () => {
    const { result } = renderHook(() => useVoucherValidate());

    await act(async () => {
      await result.current.validate({ code: "NOPE" });
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data).toBeNull();
    expect(result.current.errorKind).toBe("voucher_not_found");
    expect(result.current.error).toMatch(/not found/i);
  });

  it("classifies 400 voucher_expired", async () => {
    const { result } = renderHook(() => useVoucherValidate());

    await act(async () => {
      await result.current.validate({ code: "EXPIRED" });
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.errorKind).toBe("voucher_expired");
    expect(result.current.error).toMatch(/expired/i);
  });

  it("classifies 400 voucher_min_purchase_unmet", async () => {
    const { result } = renderHook(() => useVoucherValidate());

    await act(async () => {
      await result.current.validate({ code: "SMALLCART" });
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.errorKind).toBe("voucher_min_purchase_unmet");
    expect(result.current.error).toMatch(/minimum/i);
  });

  it("rejects empty codes without calling the server", async () => {
    const { result } = renderHook(() => useVoucherValidate());

    await act(async () => {
      await result.current.validate({ code: "   " });
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toMatch(/enter a voucher/i);
    expect(result.current.isLoading).toBe(false);
  });

  it("reset clears state", async () => {
    const { result } = renderHook(() => useVoucherValidate());
    await act(async () => {
      await result.current.validate({ code: "SUMMER25" });
    });
    await waitFor(() => expect(result.current.data).not.toBeNull());

    act(() => result.current.reset());
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
    expect(result.current.errorKind).toBeNull();
  });
});
