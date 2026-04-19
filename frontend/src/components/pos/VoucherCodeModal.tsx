"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, Ticket, X } from "lucide-react";
import { useVoucherValidate } from "@/hooks/use-voucher-validate";
import { computeVoucherDiscount, type CartVoucher } from "@/contexts/pos-cart-context";
import { cn } from "@/lib/utils";

interface VoucherCodeModalProps {
  open: boolean;
  cartSubtotal: number;
  onApply: (voucher: CartVoucher) => void;
  onCancel: () => void;
  /** Initial code to prefill (e.g. from keypad). */
  initialCode?: string;
}

function fmtEgp(n: number): string {
  return n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/**
 * VoucherCodeModal (Phase 1b — preserved from #463 for Terminal v2).
 *
 * Flow:
 *   1. User types code -> F12 / Apply -> `validate` call
 *   2. On success, render preview (discount type, value, resolved EGP amount)
 *   3. User clicks Confirm -> onApply({ code, discount_type, value, discount })
 *
 * Esc closes. Initial focus lands on the input. The input carries
 * `data-pos-scanner-ignore` so keyboard shortcuts don't fire while typing.
 */
export function VoucherCodeModal({
  open,
  cartSubtotal,
  onApply,
  onCancel,
  initialCode = "",
}: VoucherCodeModalProps) {
  const [code, setCode] = useState(initialCode);
  const inputRef = useRef<HTMLInputElement>(null);
  const validator = useVoucherValidate();

  useEffect(() => {
    if (open) {
      setCode(initialCode);
      validator.reset();
      // Defer focus to next tick so the input is in the DOM
      setTimeout(() => inputRef.current?.focus(), 0);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, initialCode]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onCancel();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onCancel]);

  if (!open) return null;

  async function handleValidate() {
    try {
      await validator.validate(code, cartSubtotal);
    } catch {
      // error surface already in validator.error
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validator.data) {
      handleValidate();
      return;
    }
    // Confirm: compute final discount and apply
    const resolved = computeVoucherDiscount(
      validator.data.discount_type,
      Number(validator.data.value),
      cartSubtotal,
    );
    onApply({
      code: validator.data.code,
      discount_type: validator.data.discount_type,
      value: Number(validator.data.value),
      discount: resolved,
    });
  }

  const preview = validator.data;
  const resolvedDiscount = preview
    ? computeVoucherDiscount(preview.discount_type, Number(preview.value), cartSubtotal)
    : 0;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="voucher-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      onClick={onCancel}
    >
      <form
        onClick={(e) => e.stopPropagation()}
        onSubmit={handleSubmit}
        className={cn(
          "w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-2xl",
        )}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-amber-500/15 text-amber-400">
              <Ticket className="h-5 w-5" />
            </div>
            <div>
              <h2 id="voucher-modal-title" className="text-base font-semibold text-text-primary">
                Apply voucher
              </h2>
              <p className="text-xs text-text-secondary">
                Enter the discount code supplied to the customer.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onCancel}
            aria-label="Close voucher modal"
            className="rounded-lg p-1 text-text-secondary hover:bg-surface-raised"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mt-5 space-y-3">
          <label className="block text-xs font-medium uppercase tracking-wider text-text-secondary">
            Voucher code
            <input
              ref={inputRef}
              data-pos-scanner-ignore=""
              value={code}
              onChange={(e) => {
                setCode(e.target.value.toUpperCase());
                if (validator.data || validator.error) validator.reset();
              }}
              placeholder="SAVE10"
              autoComplete="off"
              className={cn(
                "mt-1 block w-full rounded-xl border border-border bg-surface-raised px-3 py-2",
                "font-mono text-base tracking-widest text-text-primary placeholder:text-text-secondary",
                "focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/40",
              )}
            />
          </label>

          {validator.error && !preview && (
            <p role="alert" className="text-xs text-destructive">
              {validator.error}
            </p>
          )}

          {preview && (
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3">
              <div className="flex items-center justify-between text-xs">
                <span className="font-mono uppercase tracking-wider text-amber-400">
                  {preview.code}
                </span>
                <span className="text-text-secondary">
                  {preview.remaining_uses} use{preview.remaining_uses === 1 ? "" : "s"} left
                </span>
              </div>
              <div className="mt-2 flex items-baseline justify-between">
                <span className="text-xs text-text-secondary">
                  {preview.discount_type === "percent"
                    ? `${Number(preview.value)}% off`
                    : `Flat EGP ${fmtEgp(Number(preview.value))} off`}
                </span>
                <span className="font-mono text-lg font-semibold text-amber-400">
                  −EGP {fmtEgp(resolvedDiscount)}
                </span>
              </div>
            </div>
          )}
        </div>

        <div className="mt-5 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-xl border border-border px-4 py-2 text-sm font-medium text-text-secondary hover:bg-surface-raised"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={validator.isLoading || !code.trim()}
            className={cn(
              "inline-flex items-center gap-2 rounded-xl px-5 py-2 text-sm font-semibold",
              "bg-accent text-accent-foreground hover:bg-accent/90 disabled:opacity-40",
            )}
          >
            {validator.isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
            {preview ? "Apply voucher" : "Validate code"}
          </button>
        </div>
      </form>
    </div>
  );
}
