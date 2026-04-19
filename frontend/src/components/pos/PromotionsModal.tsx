"use client";

import { Loader2, Sparkles, X } from "lucide-react";
import { useMemo } from "react";
import { useEligiblePromotions } from "@/hooks/use-eligible-promotions";
import { usePosCart, type AppliedCartDiscount } from "@/contexts/pos-cart-context";
import { cn } from "@/lib/utils";
import type { EligiblePromotion, EligiblePromotionsRequest } from "@/types/promotions";

interface PromotionsModalProps {
  open: boolean;
  onClose: () => void;
  /** Optional drug_cluster lookup — terminal page doesn't currently track
   * cluster on cart items, so scope='category' promotions fall back to
   * subtotal-based eligibility via the backend's items+subtotal payload. */
  clusterFor?: (drugCode: string) => string | null;
}

function fmt(n: number): string {
  return n.toLocaleString("ar-EG", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatValue(type: "amount" | "percent", value: number): string {
  return type === "percent" ? `${value}%` : `EGP ${fmt(value)}`;
}

export function PromotionsModal({ open, onClose, clusterFor }: PromotionsModalProps) {
  const { items, subtotal, applyDiscount, appliedDiscount } = usePosCart();

  const request: EligiblePromotionsRequest | null = useMemo(() => {
    if (!open || items.length === 0) return null;
    return {
      items: items.map((i) => ({
        drug_code: i.drug_code,
        drug_cluster: clusterFor ? clusterFor(i.drug_code) : null,
        quantity: i.quantity,
        unit_price: i.unit_price,
      })),
      subtotal,
    };
  }, [open, items, subtotal, clusterFor]);

  const { data, error, isLoading } = useEligiblePromotions(request, open);
  const promotions = data?.promotions ?? [];

  function handleApply(promo: EligiblePromotion) {
    const discount: AppliedCartDiscount = {
      source: "promotion",
      ref: String(promo.id),
      label: promo.name,
      discountAmount: promo.preview_discount,
    };
    applyDiscount(discount);
    onClose();
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-2xl border border-border bg-surface shadow-2xl">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-accent" />
            <span className="text-sm font-semibold text-text-primary">
              Eligible promotions
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded-lg p-1 text-text-secondary hover:bg-surface-raised"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="max-h-[60vh] overflow-y-auto p-4">
          {items.length === 0 && (
            <p className="text-sm text-text-secondary">
              Add items to the cart to see eligible promotions.
            </p>
          )}

          {items.length > 0 && isLoading && (
            <div
              className="flex items-center justify-center gap-2 py-8 text-sm text-text-secondary"
              role="status"
            >
              <Loader2 className="h-4 w-4 animate-spin" />
              Checking eligibility…
            </div>
          )}

          {error && (
            <p className="text-sm text-destructive" role="alert">
              Could not load promotions. Try again.
            </p>
          )}

          {!isLoading && !error && items.length > 0 && promotions.length === 0 && (
            <p className="text-sm text-text-secondary">
              No eligible promotions for this cart.
            </p>
          )}

          <ul className="space-y-2">
            {promotions.map((p) => {
              const isApplied =
                appliedDiscount?.source === "promotion" &&
                appliedDiscount.ref === String(p.id);
              return (
                <li
                  key={p.id}
                  className={cn(
                    "rounded-lg border p-3 transition",
                    isApplied
                      ? "border-accent bg-accent/5"
                      : "border-border hover:border-accent/50",
                  )}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-text-primary">
                        {p.name}
                      </p>
                      {p.description && (
                        <p className="mt-0.5 truncate text-xs text-text-secondary">
                          {p.description}
                        </p>
                      )}
                      <p className="mt-1 text-xs text-text-secondary">
                        {formatValue(p.discount_type, p.value)} off ·{" "}
                        <span className="capitalize">{p.scope}</span>
                        {p.min_purchase ? ` · min EGP ${fmt(p.min_purchase)}` : ""}
                      </p>
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-1">
                      <span className="text-sm font-bold tabular-nums text-green-400">
                        -EGP {fmt(p.preview_discount)}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleApply(p)}
                        disabled={isApplied}
                        className={cn(
                          "rounded-md px-3 py-1 text-xs font-medium transition",
                          isApplied
                            ? "cursor-default bg-accent/20 text-accent"
                            : "bg-accent text-white hover:opacity-90",
                        )}
                      >
                        {isApplied ? "Applied" : "Apply"}
                      </button>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </div>
  );
}
