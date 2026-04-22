"use client";

import { Phone, UserCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PosCustomerLookup } from "@/hooks/use-pos-customer-lookup";

/**
 * Customer bar — top of the Cart column per v9 handoff §1.3.
 *
 * Phone input (violet icon, `dir="ltr"` because digits stay LTR even
 * inside an RTL document) on top; resolved customer card below. When
 * there's no match, the customer-card area renders a subtle "new walk-in"
 * placeholder instead of disappearing — keeps the cart column's visual
 * rhythm stable.
 *
 * Pure view — owns no lookup state. Terminal page runs
 * `usePosCustomerLookup(phone)` and passes `customer` + `isLoading`
 * down. That way the terminal can also feed the resolved customer
 * to the {@link ChurnAlertCard} next to this component without
 * re-subscribing to the hook twice.
 */
interface CustomerBarProps {
  phone: string;
  onPhoneChange: (v: string) => void;
  customer: PosCustomerLookup | null;
  isLoading: boolean;
  className?: string;
}

export function CustomerBar({
  phone,
  onPhoneChange,
  customer,
  isLoading,
  className,
}: CustomerBarProps) {
  return (
    <div
      className={cn("flex flex-col gap-2", className)}
      data-testid="customer-bar"
    >
      {/* Phone input */}
      <label className="relative block">
        <span className="sr-only">Customer phone</span>
        <Phone
          className={cn(
            "pointer-events-none absolute end-4 top-1/2 h-4 w-4 -translate-y-1/2",
            "text-[var(--pos-purple)]",
          )}
          aria-hidden="true"
        />
        <input
          type="tel"
          inputMode="numeric"
          autoComplete="tel"
          dir="ltr"
          value={phone}
          onChange={(e) => onPhoneChange(e.target.value)}
          placeholder="رقم هاتف العميل · 01XXXXXXXXX"
          data-pos-scanner-ignore=""
          data-testid="customer-phone-input"
          aria-label="Customer phone"
          className={cn(
            "w-full rounded-xl border border-[var(--pos-line)] bg-[var(--pos-bg)]",
            "py-3 pe-12 ps-4 font-mono text-sm text-[var(--pos-ink)]",
            "placeholder:text-[var(--pos-ink-3)] focus:outline-none",
            "focus:border-[var(--pos-purple)]/60",
          )}
        />
      </label>

      {/* Customer card (resolved / loading / empty) */}
      {isLoading ? (
        <div
          data-testid="customer-card-loading"
          aria-live="polite"
          className={cn(
            "h-[58px] animate-pulse rounded-xl border border-[var(--pos-line)]",
            "bg-[var(--pos-panel-2)]/40",
          )}
        />
      ) : customer ? (
        <div
          data-testid="customer-card"
          className={cn(
            "flex items-center justify-between gap-3 rounded-xl border",
            "border-[var(--pos-line)] bg-[var(--pos-panel-2)]/60 p-3",
          )}
        >
          <div className="flex items-center gap-3">
            <div
              className={cn(
                "grid h-9 w-9 place-items-center rounded-lg",
                "bg-[var(--pos-purple)]/15 text-[var(--pos-purple)]",
              )}
            >
              <UserCheck className="h-5 w-5" aria-hidden="true" />
            </div>
            <div className="flex flex-col" dir="rtl">
              <p className="font-arabic text-sm font-bold text-[var(--pos-ink)]">
                {customer.customer_name}
                {customer.loyalty_tier === "VIP" && (
                  <span
                    className={cn(
                      "ms-2 rounded px-1.5 py-0.5 font-mono text-[9px] font-bold",
                      "bg-[var(--pos-gold)]/15 text-[var(--pos-gold)]",
                    )}
                  >
                    VIP
                  </span>
                )}
              </p>
              <p className="font-arabic text-[11px] text-[var(--pos-ink-3)]">
                نقاط الولاء: {customer.loyalty_points.toLocaleString("ar-EG")}
              </p>
            </div>
          </div>
          <div className="text-end" dir="ltr">
            <p className="pos-eyebrow text-[9px]">Credit</p>
            <p
              className={cn(
                "font-mono text-sm font-bold tabular-nums",
                customer.outstanding_credit_egp < 0
                  ? "text-[var(--pos-red)]"
                  : customer.outstanding_credit_egp > 0
                    ? "text-[var(--pos-green)]"
                    : "text-[var(--pos-ink-3)]",
              )}
              data-testid="customer-credit"
            >
              {customer.outstanding_credit_egp === 0
                ? "—"
                : `${customer.outstanding_credit_egp < 0 ? "-" : "+"}${Math.abs(customer.outstanding_credit_egp).toFixed(2)}`}
            </p>
          </div>
        </div>
      ) : (
        phone.length > 0 && (
          <div
            data-testid="customer-card-walkin"
            className={cn(
              "rounded-xl border border-dashed border-[var(--pos-line)]",
              "bg-[var(--pos-bg)] px-3 py-2",
              "font-arabic text-[11px] text-[var(--pos-ink-3)]",
            )}
            dir="rtl"
          >
            عميل جديد · اضغط لإنشاء ملف
          </div>
        )
      )}
    </div>
  );
}
