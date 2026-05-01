import { describe, it, expect, beforeEach } from "vitest";
import { http, HttpResponse } from "msw";
import { renderHook, act } from "@testing-library/react";
import { server } from "../mocks/server";
import { usePosCheckout } from "@pos/hooks/use-pos-checkout";

interface CapturedRequest {
  body: unknown;
  idempotencyKey: string | null;
}

const captured: CapturedRequest[] = [];

function primeAddItemHandler() {
  server.use(
    http.post(
      "*/api/v1/pos/transactions/:txnId/items",
      async ({ request }) => {
        const body = await request.json();
        captured.push({
          body,
          idempotencyKey: request.headers.get("Idempotency-Key"),
        });
        return HttpResponse.json({
          drug_code: (body as { drug_code: string }).drug_code,
          drug_name: (body as { drug_name: string }).drug_name,
          batch_number: null,
          expiry_date: null,
          quantity: (body as { quantity: number }).quantity,
          unit_price: (body as { unit_price: number }).unit_price,
          discount: 0,
          line_total: 0,
          is_controlled: false,
        });
      },
    ),
  );
}

describe("usePosCheckout.addItem", () => {
  beforeEach(() => {
    captured.length = 0;
    primeAddItemHandler();
  });

  it("sends Idempotency-Key on every POST /items call", async () => {
    const { result } = renderHook(() => usePosCheckout());
    await act(async () => {
      await result.current.addItem(1001, {
        drug_code: "SKU-A",
        drug_name: "Drug A",
        quantity: 1,
        unit_price: 10,
      });
    });
    expect(captured).toHaveLength(1);
    expect(captured[0].idempotencyKey).toBeTruthy();
    // Loose UUID-ish shape check — the hook mints a v4 UUID via crypto.randomUUID.
    expect(captured[0].idempotencyKey?.length ?? 0).toBeGreaterThan(20);
  });

  it("mints a unique Idempotency-Key per call (replays must not dedupe)", async () => {
    const { result } = renderHook(() => usePosCheckout());
    await act(async () => {
      await result.current.addItem(1001, {
        drug_code: "SKU-A",
        drug_name: "Drug A",
        quantity: 1,
        unit_price: 10,
      });
      await result.current.addItem(1001, {
        drug_code: "SKU-B",
        drug_name: "Drug B",
        quantity: 1,
        unit_price: 20,
      });
    });
    expect(captured).toHaveLength(2);
    expect(captured[0].idempotencyKey).not.toBe(captured[1].idempotencyKey);
  });

  // Regression — screenshot 2026-04-30 showed pydantic rejecting a numeric
  // drug_code with {"loc":["body","drug_code"],"msg":"Input should be a
  // valid string","input":3210570}. The hook now defensively coerces.
  it("coerces a numeric drug_code to string before POSTing", async () => {
    const { result } = renderHook(() => usePosCheckout());
    await act(async () => {
      await result.current.addItem(1001, {
        // Intentionally numeric — simulates upstream type pollution.
        drug_code: 3210570 as unknown as string,
        drug_name: "Numeric SKU drug",
        quantity: 1,
        unit_price: 50,
      });
    });
    const sent = (captured[0].body as { drug_code: unknown }).drug_code;
    expect(typeof sent).toBe("string");
    expect(sent).toBe("3210570");
  });
});
