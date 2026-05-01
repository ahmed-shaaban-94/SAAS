import { useState } from "react";
import { AlertTriangle, Loader2, X } from "lucide-react";
import { voidTransaction } from "@pos/hooks/use-pos-returns";
import { cn } from "@shared/lib/utils";
import type { TransactionResponse } from "@pos/types/pos";

interface VoidModalProps {
  transaction: TransactionResponse;
  onSuccess: () => void;
  onCancel: () => void;
}

function fmt(n: number): string {
  return n.toLocaleString("ar-EG", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function VoidModal({ transaction, onSuccess, onCancel }: VoidModalProps) {
  const [reason, setReason] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleVoid() {
    if (reason.trim().length < 3) {
      setError("Reason must be at least 3 characters");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      await voidTransaction(transaction.id, reason.trim());
      onSuccess();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to void transaction");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-surface shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-destructive" />
            <span className="text-sm font-semibold text-text-primary">Void Transaction</span>
          </div>
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg p-1 text-text-secondary hover:bg-surface-raised"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="space-y-4 p-4">
          {/* Transaction summary */}
          <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-text-secondary">
                Receipt #{transaction.receipt_number ?? transaction.id}
              </span>
              <span className="text-sm font-bold tabular-nums text-destructive">
                EGP {fmt(transaction.grand_total)}
              </span>
            </div>
            <p className="mt-1 text-xs text-text-secondary">
              {new Date(transaction.created_at).toLocaleString()}
            </p>
          </div>

          <p className="text-xs text-text-secondary">
            This action cannot be undone. The transaction will be marked as voided and the
            reason recorded in the audit log.
          </p>

          {/* Reason input */}
          <div>
            <label className="mb-1 block text-xs font-medium text-text-secondary">
              Void Reason <span className="text-destructive">*</span>
            </label>
            <textarea
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Describe why this transaction is being voided…"
              className={cn(
                "w-full resize-none rounded-xl border border-border bg-surface px-3 py-2",
                "text-sm text-text-primary placeholder:text-text-secondary",
                "focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent",
              )}
            />
          </div>

          {error && (
            <p className="text-xs text-destructive">{error}</p>
          )}

          {/* Actions */}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 rounded-xl border border-border py-2.5 text-sm font-medium text-text-secondary hover:bg-surface-raised"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleVoid}
              disabled={isLoading || reason.trim().length < 3}
              className={cn(
                "flex flex-1 items-center justify-center gap-2 rounded-xl py-2.5",
                "bg-destructive text-sm font-semibold text-white",
                "hover:bg-destructive/90 disabled:pointer-events-none disabled:opacity-40",
              )}
            >
              {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
              Void Transaction
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
