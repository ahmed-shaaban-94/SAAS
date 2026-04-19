"use client";

import { Printer, Mail, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { TransactionDetailResponse, CheckoutResponse } from "@/types/pos";

interface AppliedVoucherInfo {
  code: string;
  discount_amount: number;
}

interface ReceiptPreviewProps {
  transaction: TransactionDetailResponse;
  checkoutResult: CheckoutResponse;
  /** When present, renders an explicit "Voucher <CODE>" line under
   * the discount row. Passed in from the checkout page so the receipt
   * can show the redeemed code even after the cart has been cleared. */
  voucher?: AppliedVoucherInfo | null;
  onPrint?: () => void;
  onEmail?: () => void;
  onClose: () => void;
}

function fmt(n: number): string {
  return n.toLocaleString("ar-EG", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function ReceiptPreview({
  transaction,
  checkoutResult,
  voucher,
  onPrint,
  onEmail,
  onClose,
}: ReceiptPreviewProps) {
  return (
    <div className="flex flex-col items-center gap-6">
      {/* Success indicator */}
      <div className="flex flex-col items-center gap-2">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-green-500/20">
          <CheckCircle2 className="h-8 w-8 text-green-400" />
        </div>
        <h2 className="text-lg font-bold text-text-primary">Payment Complete</h2>
        <p className="text-sm text-text-secondary">Receipt #{checkoutResult.receipt_number}</p>
      </div>

      {/* Receipt card */}
      <div className="w-full max-w-sm rounded-xl border border-border bg-surface p-4 font-mono text-xs">
        <div className="mb-3 text-center">
          <p className="font-semibold text-sm text-text-primary">DataPulse Pharmacy</p>
          <p className="text-text-secondary">{new Date(transaction.created_at).toLocaleString()}</p>
          <p className="text-text-secondary">Site: {transaction.site_code}</p>
        </div>

        <div className="divide-y divide-border/50">
          {transaction.items.map((item, i) => (
            <div key={i} className="py-2">
              <div className="flex justify-between gap-2">
                <span className="flex-1 truncate text-text-primary">{item.drug_name}</span>
                <span className="tabular-nums text-text-secondary">
                  {item.quantity}×{fmt(item.unit_price)}
                </span>
              </div>
              {item.batch_number && (
                <p className="text-text-secondary">
                  B:{item.batch_number} Exp:{item.expiry_date ?? "—"}
                </p>
              )}
              <div className="flex justify-end">
                <span className="tabular-nums text-text-primary">EGP {fmt(item.line_total)}</span>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-2 space-y-1 border-t border-border/50 pt-2">
          <div className="flex justify-between">
            <span className="text-text-secondary">Subtotal</span>
            <span className="tabular-nums">EGP {fmt(transaction.subtotal)}</span>
          </div>
          {transaction.discount_total > 0 && (
            <div className="flex justify-between text-green-400">
              <span>Discount</span>
              <span className="tabular-nums">-EGP {fmt(transaction.discount_total)}</span>
            </div>
          )}
          {voucher && (
            <div className="flex justify-between text-amber-400">
              <span>Voucher {voucher.code}</span>
              <span className="tabular-nums">-EGP {fmt(voucher.discount_amount)}</span>
            </div>
          )}
          <div className="flex justify-between font-semibold">
            <span>TOTAL</span>
            <span className="tabular-nums">EGP {fmt(transaction.grand_total)}</span>
          </div>
          <div className="flex justify-between text-text-secondary">
            <span>Method</span>
            <span className="uppercase">{transaction.payment_method}</span>
          </div>
          {checkoutResult.change_amount > 0 && (
            <div className="flex justify-between text-green-400">
              <span>Change</span>
              <span className="tabular-nums">EGP {fmt(checkoutResult.change_amount)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex w-full max-w-sm gap-3">
        {onPrint && (
          <button
            type="button"
            onClick={onPrint}
            className={cn(
              "flex flex-1 items-center justify-center gap-2 rounded-xl border border-border",
              "py-3 text-sm font-medium text-text-secondary hover:bg-surface-raised",
            )}
          >
            <Printer className="h-4 w-4" />
            Print
          </button>
        )}
        {onEmail && (
          <button
            type="button"
            onClick={onEmail}
            className={cn(
              "flex flex-1 items-center justify-center gap-2 rounded-xl border border-border",
              "py-3 text-sm font-medium text-text-secondary hover:bg-surface-raised",
            )}
          >
            <Mail className="h-4 w-4" />
            Email
          </button>
        )}
        <button
          type="button"
          onClick={onClose}
          className={cn(
            "flex flex-1 items-center justify-center rounded-xl",
            "bg-accent py-3 text-sm font-semibold text-accent-foreground",
            "shadow-[0_8px_24px_rgba(0,199,242,0.2)] hover:bg-accent/90",
          )}
        >
          New Sale
        </button>
      </div>
    </div>
  );
}
