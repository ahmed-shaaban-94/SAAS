import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, ChevronLeft, ChevronRight, Printer, RefreshCw, RotateCcw, XCircle } from "lucide-react";
import { VoidModal } from "@pos/components/VoidModal";
import { usePosHistory } from "@pos/hooks/use-pos-history";
import { useSession } from "@shared/lib/auth-bridge";
import { fetchAPI } from "@shared/lib/api-client";
import { buildReceiptPayload, printReceipt } from "@pos/lib/print-bridge";
import { usePosBranding } from "@pos/hooks/use-pos-branding";
import { cn } from "@shared/lib/utils";
import type { TransactionDetailResponse, TransactionResponse, TransactionStatus, CheckoutResponse } from "@pos/types/pos";

const STATUS_COLORS: Record<TransactionStatus, string> = {
  draft: "text-text-secondary bg-white/[0.04]",
  completed: "text-emerald-300 bg-emerald-400/10",
  voided: "text-[#ff7b7b] bg-[rgba(255,123,123,0.1)]",
  returned: "text-amber-300 bg-amber-400/10",
};

function fmt(n: number): string {
  return n.toLocaleString("ar-EG", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function PosHistoryPage() {
  const navigate = useNavigate();
  const { data: session } = useSession();
  const { branding: posBranding } = usePosBranding();
  const [page, setPage] = useState(1);
  const limit = 15;

  const { transactions, total, isLoading, isError, mutate } = usePosHistory({ page, limit });

  const totalPages = Math.ceil(total / limit);

  // Void modal state
  const [voidTarget, setVoidTarget] = useState<TransactionResponse | null>(null);

  // Per-row reprint state — { [txnId]: "printing" | "error" }
  const [reprintState, setReprintState] = useState<Record<number, "printing" | "error">>({});

  function handleVoidSuccess() {
    setVoidTarget(null);
    void mutate();
  }

  async function handleReprint(txn: TransactionResponse) {
    setReprintState((s) => ({ ...s, [txn.id]: "printing" }));
    try {
      const detail = await fetchAPI<TransactionDetailResponse>(
        `/api/v1/pos/transactions/${txn.id}`,
      );
      const payload = buildReceiptPayload({
        txn: detail,
        result: { receipt_number: txn.receipt_number ?? `TXN-${txn.id}` } as CheckoutResponse,
        staffName: session?.user?.name ?? "",
        storeName: posBranding.invoiceLabel,
        storeAddress: posBranding.branchAddress,
        confirmation: "confirmed",
      });
      await printReceipt(payload);
      setReprintState((s) => {
        const { [txn.id]: _omit, ...rest } = s;
        return rest;
      });
    } catch {
      setReprintState((s) => ({ ...s, [txn.id]: "error" }));
      // Auto-clear error after 3s so the cashier can retry
      setTimeout(() => {
        setReprintState((s) => {
          const { [txn.id]: _omit, ...rest } = s;
          return rest;
        });
      }, 3000);
    }
  }

  return (
    <div className="pos-root flex min-h-screen flex-col">
      <header className="flex h-14 items-center justify-between border-b border-[var(--pos-line)] bg-[var(--pos-card)] px-4">
        <button
          type="button"
          onClick={() => navigate("/terminal")}
          className="flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>
        <span className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-cyan-300">
          ● History
        </span>
        <button
          type="button"
          onClick={() => mutate()}
          aria-label="Refresh"
          className="rounded-lg p-1.5 text-text-secondary hover:bg-[var(--pos-card)]"
        >
          <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
        </button>
      </header>

      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col overflow-y-auto p-4">
        <div className="mb-4">
          <h1 className="font-[family-name:var(--font-fraunces)] text-2xl italic text-text-primary">
            Every receipt from this shift
          </h1>
          <p className="mt-1 text-xs text-text-secondary">
            Ring-up order, newest first. Tap a completed sale to return or void.
          </p>
        </div>

        {isError && (
          <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-center text-sm text-destructive">
            Failed to load history
          </div>
        )}

        {isLoading && !transactions.length && (
          <div className="space-y-2">
            {Array.from({ length: 8 }, (_, i) => (
              <div key={i} className="h-20 animate-pulse rounded-xl bg-[var(--pos-card)]" />
            ))}
          </div>
        )}

        {!isLoading && transactions.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-text-secondary">
            <div className="font-[family-name:var(--font-fraunces)] text-lg italic text-text-primary">
              All clear.
            </div>
            <p className="mt-1 text-xs">No transactions found.</p>
          </div>
        )}

        <div className="space-y-2">
          {transactions.map((txn) => (
            <div
              key={txn.id}
              className="rounded-xl border border-[var(--pos-line)] bg-[var(--pos-card)] p-3 transition-colors hover:border-cyan-400/30"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-semibold tabular-nums text-text-primary">
                      #{txn.receipt_number ?? txn.id}
                    </span>
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 font-mono text-[9px] font-bold uppercase tracking-wider",
                        STATUS_COLORS[txn.status],
                      )}
                    >
                      {txn.status}
                    </span>
                  </div>
                  <p className="mt-0.5 text-xs text-text-secondary">
                    {new Date(txn.created_at).toLocaleString()} · {txn.payment_method ?? "—"}
                  </p>
                  {txn.customer_id && (
                    <p className="text-xs text-text-secondary">Customer: {txn.customer_id}</p>
                  )}
                </div>
                <div className="text-right">
                  <p className="font-mono text-sm font-semibold tabular-nums text-cyan-300">
                    EGP {fmt(txn.grand_total)}
                  </p>
                </div>
              </div>

              {/* Action buttons — only for completed transactions */}
              {txn.status === "completed" && (
                <div className="mt-2 flex gap-2 border-t border-[var(--pos-line)] pt-2">
                  <button
                    type="button"
                    onClick={() => void handleReprint(txn)}
                    disabled={reprintState[txn.id] === "printing"}
                    data-testid={`reprint-${txn.id}`}
                    className={cn(
                      "flex flex-1 items-center justify-center gap-1.5 rounded-lg py-1.5",
                      "border border-cyan-400/30 bg-cyan-400/10 text-xs font-medium text-cyan-300",
                      "hover:bg-cyan-400/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed",
                      reprintState[txn.id] === "error" && "border-destructive/30 bg-destructive/10 text-destructive",
                    )}
                  >
                    <Printer className={cn("h-3 w-3", reprintState[txn.id] === "printing" && "animate-pulse")} />
                    {reprintState[txn.id] === "printing"
                      ? "Printing\u2026"
                      : reprintState[txn.id] === "error"
                        ? "Failed"
                        : "Reprint"}
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      navigate(`/pos-returns?txn=${txn.id}`)
                    }
                    className={cn(
                      "flex flex-1 items-center justify-center gap-1.5 rounded-lg py-1.5",
                      "border border-amber-500/30 bg-amber-500/10 text-xs font-medium text-amber-400",
                      "hover:bg-amber-500/20 transition-colors",
                    )}
                  >
                    <RotateCcw className="h-3 w-3" />
                    Return
                  </button>
                  <button
                    type="button"
                    onClick={() => setVoidTarget(txn)}
                    className={cn(
                      "flex flex-1 items-center justify-center gap-1.5 rounded-lg py-1.5",
                      "border border-destructive/30 bg-destructive/10 text-xs font-medium text-destructive",
                      "hover:bg-destructive/20 transition-colors",
                    )}
                  >
                    <XCircle className="h-3 w-3" />
                    Void
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="mt-4 flex items-center justify-center gap-2">
            <button
              type="button"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-[var(--pos-line)] disabled:opacity-40"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="font-mono text-xs text-text-secondary">
              {page} / {totalPages}
            </span>
            <button
              type="button"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-[var(--pos-line)] disabled:opacity-40"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </main>

      {/* Void modal */}
      {voidTarget && (
        <VoidModal
          transaction={voidTarget}
          onSuccess={handleVoidSuccess}
          onCancel={() => setVoidTarget(null)}
        />
      )}
    </div>
  );
}
