import { useState } from "react";
import { Loader2, RotateCcw } from "lucide-react";
import { processReturn } from "@pos/hooks/use-pos-returns";
import { cn } from "@shared/lib/utils";
import type { PosCartItem, ReturnReason, ReturnResponse, TransactionDetailResponse } from "@pos/types/pos";

interface ReturnFormProps {
  transaction: TransactionDetailResponse;
  onSuccess: (result: ReturnResponse) => void;
}

const RETURN_REASONS: { value: ReturnReason; label: string }[] = [
  { value: "defective", label: "Defective / Damaged" },
  { value: "wrong_drug", label: "Wrong Drug Dispensed" },
  { value: "expired", label: "Expired Product" },
  { value: "customer_request", label: "Customer Request" },
];

function fmt(n: number): string {
  return n.toLocaleString("ar-EG", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function ReturnForm({ transaction, onSuccess }: ReturnFormProps) {
  const [reason, setReason] = useState<ReturnReason>("customer_request");
  const [refundMethod, setRefundMethod] = useState<"cash" | "credit_note">("cash");
  const [notes, setNotes] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setIsLoading(true);
    setError(null);
    try {
      // Send full PosCartItem array as required by backend ReturnRequest
      const items: PosCartItem[] = transaction.items.map((item) => ({
        drug_code: item.drug_code,
        drug_name: item.drug_name,
        batch_number: item.batch_number,
        expiry_date: item.expiry_date,
        quantity: item.quantity,
        unit_price: item.unit_price,
        discount: item.discount,
        line_total: item.line_total,
        is_controlled: item.is_controlled,
      }));
      const result = await processReturn({
        original_transaction_id: transaction.id,
        items,
        reason,
        refund_method: refundMethod,
        notes: notes.trim() || undefined,
      });
      onSuccess(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to process return");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="space-y-5">
      {/* Original transaction summary */}
      <div className="rounded-xl border border-border bg-surface p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-text-secondary">Original Transaction</p>
            <p className="mt-0.5 text-sm font-semibold text-text-primary">
              #{transaction.receipt_number ?? transaction.id}
            </p>
            <p className="text-xs text-text-secondary">
              {new Date(transaction.created_at).toLocaleString()} · {transaction.site_code}
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-text-secondary">Total</p>
            <p className="text-lg font-bold tabular-nums text-accent">
              EGP {fmt(transaction.grand_total)}
            </p>
          </div>
        </div>
      </div>

      {/* Items summary */}
      {transaction.items.length > 0 && (
        <div className="rounded-xl border border-border bg-surface">
          <p className="border-b border-border px-4 py-2 text-xs font-medium text-text-secondary">
            Items to Return
          </p>
          <div className="divide-y divide-border/50">
            {transaction.items.map((item, i) => (
              <div key={i} className="flex items-center justify-between px-4 py-2">
                <div className="min-w-0">
                  <p className="truncate text-sm text-text-primary">{item.drug_name}</p>
                  {item.batch_number && (
                    <p className="text-xs text-text-secondary">Batch: {item.batch_number}</p>
                  )}
                </div>
                <div className="ms-2 text-end">
                  <p className="text-xs tabular-nums text-text-secondary">
                    {Number(item.quantity)} × EGP {fmt(Number(item.unit_price))}
                  </p>
                  <p className="text-sm font-medium tabular-nums text-text-primary">
                    EGP {fmt(Number(item.line_total))}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Return reason */}
      <div>
        <label className="mb-1.5 block text-xs font-medium text-text-secondary">
          Return Reason <span className="text-destructive">*</span>
        </label>
        <div className="grid grid-cols-2 gap-2">
          {RETURN_REASONS.map(({ value, label }) => (
            <button
              key={value}
              type="button"
              onClick={() => setReason(value)}
              className={cn(
                "rounded-xl border px-3 py-2.5 text-left text-xs font-medium transition-all",
                reason === value
                  ? "border-accent bg-accent/10 text-accent"
                  : "border-border bg-surface text-text-secondary hover:border-accent/40",
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Refund method */}
      <div>
        <label className="mb-1.5 block text-xs font-medium text-text-secondary">
          Refund Method
        </label>
        <div className="flex gap-2">
          {(["cash", "credit_note"] as const).map((method) => (
            <button
              key={method}
              type="button"
              onClick={() => setRefundMethod(method)}
              className={cn(
                "flex-1 rounded-xl border py-2.5 text-sm font-medium capitalize transition-all",
                refundMethod === method
                  ? "border-accent bg-accent/10 text-accent"
                  : "border-border bg-surface text-text-secondary hover:border-accent/40",
              )}
            >
              {method === "credit_note" ? "Credit Note" : "Cash"}
            </button>
          ))}
        </div>
      </div>

      {/* Notes */}
      <div>
        <label className="mb-1 block text-xs font-medium text-text-secondary">
          Notes (optional)
        </label>
        <textarea
          rows={2}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Additional details about the return…"
          className={cn(
            "w-full resize-none rounded-xl border border-border bg-surface px-3 py-2",
            "text-sm text-text-primary placeholder:text-text-secondary",
            "focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent",
          )}
        />
      </div>

      {error && <p className="text-xs text-destructive">{error}</p>}

      {/* Refund summary */}
      <div className="rounded-xl border border-green-500/20 bg-green-500/5 p-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-green-400">Refund Amount</span>
          <span className="text-lg font-bold tabular-nums text-green-400">
            EGP {fmt(transaction.grand_total)}
          </span>
        </div>
        <p className="mt-0.5 text-xs text-text-secondary">
          via {refundMethod === "credit_note" ? "Credit Note" : "Cash"}
        </p>
      </div>

      <button
        type="button"
        onClick={handleSubmit}
        disabled={isLoading}
        className={cn(
          "flex w-full items-center justify-center gap-2 rounded-xl py-3",
          "bg-accent text-sm font-semibold text-accent-foreground",
          "shadow-[0_8px_24px_rgba(0,199,242,0.2)] hover:bg-accent/90",
          "disabled:pointer-events-none disabled:opacity-40",
        )}
      >
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <RotateCcw className="h-4 w-4" />
        )}
        Process Return
      </button>
    </div>
  );
}
