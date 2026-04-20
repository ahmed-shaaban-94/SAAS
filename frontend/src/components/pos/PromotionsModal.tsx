"use client";

import { Loader2, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { ModalShell } from "@/components/pos/ModalShell";
import { useEligiblePromotions } from "@/hooks/use-eligible-promotions";
import {
  usePosCart,
  type AppliedCartDiscount,
} from "@/contexts/pos-cart-context";
import type {
  EligiblePromotion,
  EligiblePromotionsRequest,
} from "@/types/promotions";

/**
 * PromotionsModal — redesigned for PR 6.
 *
 * Design source: docs/design/pos-terminal/frames/pos/modals.jsx § PromotionsModal.
 * Contract preserved: mounted from the terminal page (or wherever promotions
 * are surfaced) with `{ open, onClose, clusterFor }`, applies an
 * `AppliedCartDiscount` via `usePosCart().applyDiscount`.
 *
 * Keyboard: 1-9 select by position, ArrowUp/Down navigate, Enter applies
 * the highlighted promotion, Esc closes (via ModalShell).
 */
export interface PromotionsModalProps {
  open: boolean;
  onClose: () => void;
  /** Optional drug_cluster lookup — terminal page doesn't currently track
   * cluster on cart items, so scope='category' promotions fall back to
   * subtotal-based eligibility via the backend's items+subtotal payload. */
  clusterFor?: (drugCode: string) => string | null;
}

function fmt(n: number): string {
  return n.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatValue(
  type: EligiblePromotion["discount_type"],
  value: number,
): string {
  return type === "percent" ? `${value}% off` : `EGP ${fmt(value)} off`;
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

  const [selected, setSelected] = useState(0);

  useEffect(() => {
    if (open) setSelected(0);
  }, [open]);

  useEffect(() => {
    if (selected >= promotions.length && promotions.length > 0) {
      setSelected(promotions.length - 1);
    }
  }, [promotions.length, selected]);

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

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelected((s) => Math.min(promotions.length - 1, s + 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelected((s) => Math.max(0, s - 1));
      } else if (/^[1-9]$/.test(e.key)) {
        const i = parseInt(e.key, 10) - 1;
        if (i < promotions.length) setSelected(i);
      } else if (e.key === "Enter") {
        const promo = promotions[selected];
        if (promo) {
          e.preventDefault();
          handleApply(promo);
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
    // applyDiscount / onClose are stable via callbacks consumed in handleApply
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, promotions, selected]);

  return (
    <ModalShell
      open={open}
      onClose={onClose}
      title="Eligible promotions"
      subtitle="Cashier-applied, admin-configured discounts that fit this cart."
      badge="PROMOTIONS"
      accent="purple"
      width={600}
      testId="pos-promotions-modal"
      titleId="pos-promotions-modal-title"
      icon={<Sparkles className="h-5 w-5" aria-hidden="true" />}
    >
      <div className="flex flex-col gap-2" data-testid="pos-promotions-list">
        {items.length === 0 && (
          <p
            className="py-6 text-center text-[13px]"
            style={{ color: "var(--pos-ink-3, #7a8494)" }}
            data-testid="pos-promotions-empty"
          >
            Add items to the cart to see eligible promotions.
          </p>
        )}

        {items.length > 0 && isLoading && (
          <div
            role="status"
            className="flex items-center justify-center gap-2 py-6"
            style={{
              color: "var(--pos-ink-3, #7a8494)",
              fontSize: 13,
            }}
          >
            <Loader2 className="h-4 w-4 animate-spin" />
            Checking eligibility…
          </div>
        )}

        {error && (
          <p
            role="alert"
            className="py-4 text-center text-[13px]"
            style={{ color: "var(--pos-red, #ff7b7b)" }}
          >
            Could not load promotions. Try again.
          </p>
        )}

        {!isLoading &&
          !error &&
          items.length > 0 &&
          promotions.length === 0 && (
            <p
              className="py-6 text-center text-[13px]"
              style={{ color: "var(--pos-ink-3, #7a8494)" }}
              data-testid="pos-promotions-empty"
            >
              No active promotions for this cart.
            </p>
          )}

        {promotions.map((p, i) => {
          const active = i === selected;
          const isApplied =
            appliedDiscount?.source === "promotion" &&
            appliedDiscount.ref === String(p.id);
          return (
            <button
              key={p.id}
              type="button"
              aria-pressed={active}
              data-active={active || undefined}
              data-testid={`pos-promotion-row-${p.id}`}
              onClick={() => setSelected(i)}
              onDoubleClick={() => handleApply(p)}
              className="relative flex items-center gap-3 text-start"
              style={{
                padding: "12px 14px",
                borderRadius: 12,
                background: active
                  ? "rgba(116,103,248,0.1)"
                  : "rgba(8,24,38,0.5)",
                border: "1.5px solid",
                borderColor: active
                  ? "var(--pos-purple, #7467f8)"
                  : "var(--pos-line, rgba(255,255,255,0.06))",
                boxShadow: active ? "0 0 20px rgba(116,103,248,0.2)" : "none",
                transition: "all 140ms ease",
                color: "var(--pos-ink, #e8ecf2)",
              }}
            >
              <span
                aria-hidden="true"
                className="absolute left-0 top-2 bottom-2 rounded-sm"
                style={{
                  width: 3,
                  background: "var(--pos-purple, #7467f8)",
                  opacity: active ? 1 : 0.4,
                }}
              />
              <div
                className="grid place-items-center font-mono"
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: 6,
                  background: "rgba(116,103,248,0.15)",
                  color: "var(--pos-purple, #7467f8)",
                  fontSize: 12,
                  fontWeight: 700,
                }}
              >
                {i + 1}
              </div>
              <div className="min-w-0 flex-1">
                <div className="mb-0.5 flex items-center gap-2">
                  <span
                    className="font-mono uppercase"
                    style={{
                      fontSize: 9.5,
                      fontWeight: 700,
                      letterSpacing: "0.18em",
                      color: "var(--pos-purple, #7467f8)",
                    }}
                  >
                    {p.discount_type === "percent" ? "PERCENT" : "AMOUNT"} ·{" "}
                    {p.scope.toUpperCase()}
                  </span>
                  <span
                    className="font-mono uppercase"
                    style={{
                      fontSize: 9,
                      letterSpacing: "0.18em",
                      color: "var(--pos-green, #1dd48b)",
                      padding: "1px 5px",
                      borderRadius: 3,
                      background: "rgba(29,212,139,0.12)",
                      border: "1px solid rgba(29,212,139,0.3)",
                    }}
                  >
                    {isApplied ? "Applied" : "Eligible"}
                  </span>
                </div>
                <div
                  className="truncate"
                  style={{ fontSize: 14, fontWeight: 600 }}
                >
                  {p.name}
                </div>
                <div
                  className="truncate"
                  style={{
                    fontSize: 12,
                    color: "var(--pos-ink-3, #7a8494)",
                    marginTop: 2,
                  }}
                >
                  {p.description ?? formatValue(p.discount_type, p.value)}
                  {p.min_purchase
                    ? ` · min EGP ${fmt(p.min_purchase)}`
                    : ""}
                </div>
              </div>
              <div className="shrink-0 text-right">
                <div
                  className="font-mono uppercase"
                  style={{
                    fontSize: 9,
                    letterSpacing: "0.18em",
                    color: "var(--pos-ink-4, #3f4a5a)",
                  }}
                >
                  Savings
                </div>
                <div
                  className="font-mono tabular-nums"
                  style={{
                    fontSize: 18,
                    fontWeight: 700,
                    color: "var(--pos-purple, #7467f8)",
                  }}
                >
                  −EGP {fmt(p.preview_discount)}
                </div>
              </div>
            </button>
          );
        })}
      </div>

      <div className="mt-3.5 flex gap-2">
        <button
          type="button"
          onClick={onClose}
          className="flex-1 rounded-xl px-4 py-3 text-[13px] font-semibold"
          style={{
            background: "transparent",
            border: "1px solid var(--pos-line, rgba(255,255,255,0.06))",
            color: "var(--pos-ink-2, #b8c0cc)",
          }}
        >
          Cancel
        </button>
        <button
          type="button"
          disabled={promotions.length === 0}
          onClick={() => {
            const promo = promotions[selected];
            if (promo) handleApply(promo);
          }}
          data-testid="pos-promotions-apply"
          className="flex-[2] rounded-xl px-4 py-3 text-[13px] font-bold"
          style={{
            background:
              promotions.length === 0
                ? "rgba(255,255,255,0.04)"
                : "linear-gradient(180deg, var(--pos-purple, #7467f8), #5a4fe0)",
            color: promotions.length === 0 ? "var(--pos-ink-4, #3f4a5a)" : "#fff",
            border:
              promotions.length === 0
                ? "1px solid var(--pos-line, rgba(255,255,255,0.06))"
                : "none",
            cursor: promotions.length === 0 ? "not-allowed" : "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 10,
          }}
        >
          Apply
          <span
            className="font-mono"
            style={{
              fontSize: 10,
              background: "rgba(0,0,0,0.25)",
              border: "1px solid rgba(0,0,0,0.3)",
              borderRadius: 4,
              padding: "2px 5px",
              color: promotions.length === 0 ? "var(--pos-ink-4, #3f4a5a)" : "#fff",
            }}
          >
            Enter
          </span>
        </button>
      </div>
    </ModalShell>
  );
}
