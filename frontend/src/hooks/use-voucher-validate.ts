"use client";

import { useCallback, useState } from "react";
import { postAPI } from "@/lib/api-client";
import type { VoucherValidateResponse } from "@/types/vouchers";

interface ValidateState {
  data: VoucherValidateResponse | null;
  isLoading: boolean;
  error: string | null;
}

const INITIAL: ValidateState = { data: null, isLoading: false, error: null };

/**
 * Thin wrapper around `POST /api/v1/pos/vouchers/validate`.
 *
 * - Normalises the code (uppercase, trimmed) before sending.
 * - Surfaces server error detail strings verbatim so the UI can render them.
 * - Caches the last successful validation in local state; callers consume
 *   `data` once it resolves and can then dispatch APPLY_VOUCHER.
 */
export function useVoucherValidate() {
  const [state, setState] = useState<ValidateState>(INITIAL);

  const validate = useCallback(
    async (code: string, cartSubtotal?: number): Promise<VoucherValidateResponse> => {
      const normalised = code.trim().toUpperCase();
      if (!normalised) {
        const err = "Enter a voucher code";
        setState({ data: null, isLoading: false, error: err });
        throw new Error(err);
      }

      setState({ data: null, isLoading: true, error: null });
      try {
        const body: { code: string; cart_subtotal?: number } = { code: normalised };
        if (typeof cartSubtotal === "number") body.cart_subtotal = cartSubtotal;
        const res = await postAPI<VoucherValidateResponse>(
          "/api/v1/pos/vouchers/validate",
          body,
        );
        setState({ data: res, isLoading: false, error: null });
        return res;
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Validation failed";
        setState({ data: null, isLoading: false, error: msg });
        throw e;
      }
    },
    [],
  );

  const reset = useCallback(() => setState(INITIAL), []);

  return { ...state, validate, reset };
}
