import { useCallback, useState } from "react";
import { postAPI, ApiError } from "@/lib/api-client";
import type { VoucherValidateResponse } from "@/types/vouchers";

/**
 * Hook for the cashier-side voucher validation flow.
 *
 * Calls `POST /api/v1/pos/vouchers/validate` with a code (and optional cart
 * subtotal). The server answers with either a validation payload describing
 * the redeemable discount, a 404 for unknown codes, or a 400 with a
 * `voucher_*` detail string for inactive / expired / exhausted / min-purchase
 * failures. The hook surfaces those three cases as flat, component-friendly
 * state: `data` / `error` / `isLoading` + a discriminated `errorKind` for
 * rendering specific messages without parsing the error string at each
 * callsite.
 */

export type VoucherValidateErrorKind =
  | "voucher_not_found"
  | "voucher_expired"
  | "voucher_not_yet_active"
  | "voucher_inactive"
  | "voucher_exhausted"
  | "voucher_min_purchase_unmet"
  | "unknown";

interface ValidateArgs {
  code: string;
  cart_subtotal?: number;
}

interface UseVoucherValidateResult {
  data: VoucherValidateResponse | null;
  error: string | null;
  errorKind: VoucherValidateErrorKind | null;
  isLoading: boolean;
  validate: (args: ValidateArgs) => Promise<VoucherValidateResponse | null>;
  reset: () => void;
}

// Map backend error detail strings -> discriminated kind used by the UI.
// Falls back to "unknown" for anything else (e.g. 500, network).
const ERROR_KIND_MAP: Record<string, VoucherValidateErrorKind> = {
  voucher_expired: "voucher_expired",
  voucher_not_yet_active: "voucher_not_yet_active",
  voucher_inactive: "voucher_inactive",
  voucher_exhausted: "voucher_exhausted",
  voucher_min_purchase_unmet: "voucher_min_purchase_unmet",
};

function classifyError(err: unknown): {
  kind: VoucherValidateErrorKind;
  message: string;
} {
  if (err instanceof ApiError) {
    if (err.status === 404) {
      return { kind: "voucher_not_found", message: "Voucher not found" };
    }
    if (err.status === 400) {
      // Look for a known "voucher_*" token inside the server message body.
      for (const [token, kind] of Object.entries(ERROR_KIND_MAP)) {
        if (err.message.includes(token)) {
          return { kind, message: humanize(kind) };
        }
      }
    }
  }
  const msg = err instanceof Error ? err.message : "Validation failed";
  return { kind: "unknown", message: msg };
}

function humanize(kind: VoucherValidateErrorKind): string {
  switch (kind) {
    case "voucher_expired":
      return "Voucher has expired";
    case "voucher_not_yet_active":
      return "Voucher is not active yet";
    case "voucher_inactive":
      return "Voucher is not active";
    case "voucher_exhausted":
      return "Voucher has no remaining uses";
    case "voucher_min_purchase_unmet":
      return "Cart subtotal below voucher minimum";
    case "voucher_not_found":
      return "Voucher not found";
    default:
      return "Could not validate voucher";
  }
}

export function useVoucherValidate(): UseVoucherValidateResult {
  const [data, setData] = useState<VoucherValidateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorKind, setErrorKind] = useState<VoucherValidateErrorKind | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setErrorKind(null);
    setIsLoading(false);
  }, []);

  const validate = useCallback(
    async ({ code, cart_subtotal }: ValidateArgs): Promise<VoucherValidateResponse | null> => {
      const trimmed = code.trim();
      if (!trimmed) {
        setData(null);
        setError("Enter a voucher code");
        setErrorKind("unknown");
        return null;
      }

      setIsLoading(true);
      setError(null);
      setErrorKind(null);
      setData(null);

      try {
        const body: { code: string; cart_subtotal?: number } = { code: trimmed };
        if (cart_subtotal !== undefined) body.cart_subtotal = cart_subtotal;
        const result = await postAPI<VoucherValidateResponse>(
          "/api/v1/pos/vouchers/validate",
          body,
        );
        setData(result);
        setIsLoading(false);
        return result;
      } catch (e) {
        const { kind, message } = classifyError(e);
        setErrorKind(kind);
        setError(message);
        setIsLoading(false);
        return null;
      }
    },
    [],
  );

  return { data, error, errorKind, isLoading, validate, reset };
}
