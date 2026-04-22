"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, CheckCircle, Loader2, RotateCcw } from "lucide-react";
import { ReturnForm } from "@/components/pos/ReturnForm";
import { fetchAPI } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { ReturnResponse, TransactionDetailResponse } from "@/types/pos";

function fmt(n: number): string {
  return n.toLocaleString("ar-EG", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function ReturnsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const txnParam = searchParams.get("txn");

  const [txnId, setTxnId] = useState(txnParam ?? "");
  const [transaction, setTransaction] = useState<TransactionDetailResponse | null>(null);
  const [isLoadingTxn, setIsLoadingTxn] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [returnResult, setReturnResult] = useState<ReturnResponse | null>(null);

  // Auto-load when txn query param is present
  useEffect(() => {
    if (txnParam) {
      loadTransaction(Number(txnParam));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [txnParam]);

  async function loadTransaction(id: number) {
    if (!id || id <= 0) {
      setLoadError("Please enter a valid transaction ID");
      return;
    }
    setIsLoadingTxn(true);
    setLoadError(null);
    setTransaction(null);
    try {
      const detail = await fetchAPI<TransactionDetailResponse>(
        `/api/v1/pos/transactions/${id}`,
      );
      if (detail.status !== "completed") {
        setLoadError(
          `Transaction #${id} cannot be returned (status: ${detail.status})`,
        );
        return;
      }
      setTransaction(detail);
    } catch {
      setLoadError(`Transaction #${id} not found`);
    } finally {
      setIsLoadingTxn(false);
    }
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const id = parseInt(txnId, 10);
    if (!Number.isNaN(id)) loadTransaction(id);
  }

  function handleReturnSuccess(result: ReturnResponse) {
    setReturnResult(result);
  }

  // ── Success state ──────────────────────────────────────────────
  if (returnResult) {
    return (
      <div className="pos-root flex min-h-screen flex-col">
        <header className="flex h-14 items-center border-b border-border bg-surface px-4">
          <span className="text-sm font-semibold text-text-primary">Return Processed</span>
        </header>
        <main className="flex flex-1 flex-col items-center justify-center gap-6 p-6">
          <div className="flex flex-col items-center gap-3 text-center">
            <CheckCircle className="h-12 w-12 text-green-400" />
            <p className="text-lg font-semibold text-text-primary">Return Successful</p>
            <p className="text-sm text-text-secondary">
              Return #{returnResult.id} recorded. Refund of{" "}
              <span className="font-medium text-green-400">
                EGP {fmt(Number(returnResult.refund_amount))}
              </span>{" "}
              via {returnResult.refund_method === "credit_note" ? "Credit Note" : "Cash"}.
            </p>
          </div>

          <div className="w-full max-w-sm space-y-2">
            <button
              type="button"
              onClick={() => {
                setReturnResult(null);
                setTransaction(null);
                setTxnId("");
              }}
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-border py-3 text-sm font-medium text-text-secondary hover:bg-surface-raised"
            >
              <RotateCcw className="h-4 w-4" />
              Process Another Return
            </button>
            <button
              type="button"
              onClick={() => router.push("/terminal")}
              className="w-full rounded-xl bg-accent py-3 text-sm font-semibold text-accent-foreground hover:bg-accent/90"
            >
              Back to Terminal
            </button>
          </div>
        </main>
      </div>
    );
  }

  // ── Main return form state ─────────────────────────────────────
  return (
    <div className="pos-root flex min-h-screen flex-col">
      <header className="flex h-14 items-center border-b border-border bg-surface px-4">
        <button
          type="button"
          onClick={() => router.back()}
          className="flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>
        <span className="ms-4 text-sm font-semibold text-text-primary">Process Return</span>
      </header>

      <main className="flex-1 overflow-y-auto p-4">
        <div className="mx-auto max-w-md space-y-4">
          {/* Transaction search */}
          {!transaction && (
            <form onSubmit={handleSearch} className="space-y-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-text-secondary">
                  Transaction ID or Receipt Number
                </label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    min="1"
                    value={txnId}
                    onChange={(e) => setTxnId(e.target.value)}
                    placeholder="Enter transaction ID…"
                    className={cn(
                      "flex-1 rounded-xl border border-border bg-surface px-4 py-3",
                      "text-sm text-text-primary placeholder:text-text-secondary",
                      "focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent",
                    )}
                  />
                  <button
                    type="submit"
                    disabled={isLoadingTxn || !txnId}
                    className={cn(
                      "flex items-center gap-2 rounded-xl bg-accent px-4 py-3",
                      "text-sm font-semibold text-accent-foreground hover:bg-accent/90",
                      "disabled:pointer-events-none disabled:opacity-40",
                    )}
                  >
                    {isLoadingTxn ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      "Load"
                    )}
                  </button>
                </div>
              </div>

              {loadError && (
                <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-3">
                  <p className="text-sm text-destructive">{loadError}</p>
                </div>
              )}
            </form>
          )}

          {/* Return form once transaction is loaded */}
          {transaction && (
            <>
              <button
                type="button"
                onClick={() => {
                  setTransaction(null);
                  setTxnId("");
                }}
                className="text-xs text-text-secondary hover:text-text-primary"
              >
                ← Search different transaction
              </button>
              <ReturnForm
                transaction={transaction}
                onSuccess={handleReturnSuccess}
              />
            </>
          )}
        </div>
      </main>
    </div>
  );
}
