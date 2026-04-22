"use client";

import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";
import { PaymentTiles } from "./PaymentTiles";
import { ActivePaymentStrip, type InsuranceState } from "./ActivePaymentStrip";
import { Keypad } from "./Keypad";
import { ChargeButton } from "./ChargeButton";
import type { TilePaymentMethod } from "./types";
import { fmtEgp } from "./types";

/**
 * Props for {@link CheckoutConfirmModal}.
 *
 * The modal is a CONTROLLED presentation surface — it owns no payment
 * state. All method/tender/insurance fields are passed in from the
 * terminal page so the existing keyboard shortcuts (F9/F10/F11) and
 * voucher/insurance modals continue to mutate the same source of truth.
 *
 * The only behaviors the modal adds on top of the existing components:
 *  - a centered Total hero (Fraunces, per the "one serif moment" rule)
 *  - Escape-to-close
 *  - backdrop-click-to-close
 *  - Enter-to-charge while the modal is open (terminal page owns the
 *    actual keydown handler; modal just signals it is open via the
 *    `open` prop so the terminal page can branch).
 */
interface CheckoutConfirmModalProps {
  open: boolean;
  itemCount: number;
  grandTotal: number;

  activePayment: TilePaymentMethod;
  onActivePaymentChange: (m: TilePaymentMethod) => void;

  cashTendered: string;
  onCashTenderedChange: (v: string) => void;

  cardLast4: string;
  onCardLast4Change: (v: string) => void;

  insurance: InsuranceState | null;
  onInsuranceChange: (next: InsuranceState | null) => void;
  onOpenInsuranceModal: () => void;

  voucherCode: string | null;
  voucherDiscount: number;
  onOpenVoucherModal: () => void;

  lastKeypadKey: string | null;

  chargeDisabled: boolean;
  onCharge: () => void;
  onClose: () => void;

  /** Backend error from a failed checkout attempt — shown inline above the
   *  charge button so the cashier can retry without dismissing the modal. */
  error?: string | null;
}

/**
 * Confirm-step modal shown after the cashier presses the right-column
 * "Start checkout" CTA (or Enter). Wraps the existing payment widgets
 * inside a focused dialog surface, per the v9 design handoff §1.3
 * "Checkout CTA → payment modal" editorial decision.
 *
 * Not a new payment pipeline — the `onCharge` prop is wired to the
 * terminal page's existing `handleCheckout` which already writes
 * `pos:pending_checkout` to localStorage and navigates to `/checkout`
 * where the transaction is actually processed.
 */
export function CheckoutConfirmModal(props: CheckoutConfirmModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);

  // Move focus into the dialog on open so Tab/Enter land inside it
  // rather than on the now-obscured terminal. We re-focus on every
  // re-mount because React may re-render the dialog when a payment
  // method switches.
  useEffect(() => {
    if (!props.open) return;
    const prev = document.activeElement as HTMLElement | null;
    dialogRef.current?.focus();
    return () => {
      // Return focus to the opener (typically the Start-checkout CTA)
      // to keep keyboard users anchored after Esc/cancel.
      prev?.focus();
    };
  }, [props.open]);

  // Modal owns Enter/Escape while it is open. The terminal page's
  // Enter handler is gated on `!checkoutOpen` so it never races with
  // this listener — first Enter opens the modal, second Enter charges.
  useEffect(() => {
    if (!props.open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        props.onClose();
        return;
      }
      if (e.key === "Enter" && !props.chargeDisabled) {
        // Allow Enter to charge even when the cash-tendered input is
        // focused. The ChargeButton's aria-label includes "(Enter)"
        // so screen readers know this.
        e.preventDefault();
        props.onCharge();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [props.open, props]);

  if (!props.open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="checkout-confirm-title"
      data-testid="checkout-confirm-modal"
      className={cn(
        "fixed inset-0 z-40 flex items-center justify-center",
        "bg-[rgba(5,14,23,0.78)] backdrop-blur-md p-4",
        "pos-no-print animate-in fade-in duration-200",
      )}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) props.onClose();
      }}
    >
      <div
        ref={dialogRef}
        tabIndex={-1}
        className={cn(
          "relative flex max-h-[min(92vh,820px)] w-full max-w-3xl flex-col overflow-hidden outline-none",
          "rounded-3xl border border-cyan-400/25 bg-[var(--pos-card)]",
          "shadow-[0_40px_80px_rgba(0,0,0,0.5),0_0_0_1px_rgba(0,199,242,0.08),0_0_80px_rgba(0,199,242,0.14)]",
          "animate-in zoom-in-95 duration-200",
        )}
      >
        {/* Header */}
        <header
          className={cn(
            "flex items-center justify-between border-b border-[var(--pos-line)] px-5 py-4",
            "bg-gradient-to-r from-[var(--pos-bg)] to-[var(--pos-card)]",
          )}
        >
          <div className="flex flex-col">
            <h2
              id="checkout-confirm-title"
              className="pos-eyebrow text-cyan-300/90"
            >
              Checkout · Confirm
            </h2>
            <p className="mt-1 text-sm text-[var(--pos-ink-2)]">
              {props.itemCount} item{props.itemCount === 1 ? "" : "s"} · pick a
              payment method
            </p>
          </div>
          <button
            type="button"
            onClick={props.onClose}
            aria-label="Close checkout"
            data-testid="checkout-confirm-close"
            className={cn(
              "grid h-9 w-9 place-items-center rounded-xl",
              "border border-[var(--pos-line)] bg-white/[0.03] text-[var(--pos-ink-2)]",
              "transition-colors hover:border-[var(--pos-red)]/50 hover:text-[var(--pos-red)]",
            )}
          >
            <X className="h-4 w-4" />
          </button>
        </header>

        {/* Grand total hero — the "one serif moment" on the checkout surface */}
        <div
          className={cn(
            "border-b border-[var(--pos-line)] px-5 py-5 text-center",
            "bg-gradient-to-b from-[var(--pos-bg)]/50 to-transparent",
          )}
        >
          <p className="pos-eyebrow mb-2">Total Due</p>
          <div className="flex items-baseline justify-center gap-2">
            <span className="font-mono text-sm font-semibold text-[var(--pos-ink-2)]">
              EGP
            </span>
            <span
              className="pos-grand-total text-7xl leading-none"
              data-testid="checkout-confirm-total"
            >
              {fmtEgp(props.grandTotal)}
            </span>
          </div>
        </div>

        {/* Body — payment tiles + strip on left, keypad on right */}
        <div className="flex-1 overflow-y-auto p-5">
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
            {/* Left column */}
            <div className="flex flex-col gap-3">
              <PaymentTiles
                active={props.activePayment}
                onSelect={(m) => {
                  props.onActivePaymentChange(m);
                  if (m === "voucher" && !props.voucherCode)
                    props.onOpenVoucherModal();
                }}
                voucherCode={props.voucherCode}
                voucherDiscount={props.voucherDiscount}
                insuranceCoveragePct={props.insurance?.coveragePct ?? null}
              />
              <ActivePaymentStrip
                method={props.activePayment}
                grandTotal={props.grandTotal}
                cashTendered={props.cashTendered}
                onCashTenderedChange={props.onCashTenderedChange}
                cardLast4={props.cardLast4}
                onCardLast4Change={props.onCardLast4Change}
                insurance={props.insurance}
                onInsuranceChange={props.onInsuranceChange}
                onOpenInsuranceModal={props.onOpenInsuranceModal}
                voucherCode={props.voucherCode}
                voucherDiscount={props.voucherDiscount}
                onOpenVoucherModal={props.onOpenVoucherModal}
              />
            </div>

            {/* Right column — keypad (cash-only) + shortcut hint */}
            <div className="flex flex-col gap-3">
              <Keypad
                value={props.cashTendered}
                onChange={props.onCashTenderedChange}
                disabled={props.activePayment !== "cash"}
                lastKey={props.lastKeypadKey}
              />
              <p className="pos-eyebrow text-center text-[var(--pos-ink-3)]">
                Esc to cancel · Enter to charge
              </p>
            </div>
          </div>
        </div>

        {/* Footer — single charge action */}
        <footer className="border-t border-[var(--pos-line)] p-4">
          {props.error && (
            <p
              role="alert"
              data-testid="checkout-confirm-error"
              className="mb-3 text-center text-xs text-[var(--pos-red)]"
            >
              {props.error}
            </p>
          )}
          <ChargeButton
            grandTotal={props.grandTotal}
            disabled={props.chargeDisabled}
            onCharge={props.onCharge}
          />
        </footer>
      </div>
    </div>
  );
}
