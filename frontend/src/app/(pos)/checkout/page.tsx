"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { ArrowLeft, FileText, Loader2 } from "lucide-react";
import { PaymentPanel } from "@/components/pos/PaymentPanel";
import { ReceiptPreview } from "@/components/pos/ReceiptPreview";
import { InvoiceModal } from "@/components/pos/InvoiceModal";
import { OfflineBadge } from "@/components/pos/OfflineBadge";
import { usePosCart } from "@/hooks/use-pos-cart";
import { usePosCheckout } from "@/hooks/use-pos-checkout";
import { fetchAPI, postAPI } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type {
  PaymentMethod,
  CheckoutResponse,
  TransactionDetailResponse,
} from "@/types/pos";

// Branch metadata for the A4 invoice header. These are display-only and
// come from the design handoff; wire to a real tenant-settings endpoint
// once the branding surface exposes them.
const INVOICE_BRANCH_NAME = "Maadi branch · POS-03";
const INVOICE_BRANCH_ADDRESS = "12 Sobhi Saleh St · Cairo";
const INVOICE_TAX_NUMBER = "428-893-011";

interface PendingCheckout {
  transactionId: number;
  method: PaymentMethod;
  /** Optional — present when the insurance payment flow captured a
   * pre-auth / policy reference in the InsuranceModal. */
  insuranceNo?: string;
}

export default function CheckoutPage() {
  const router = useRouter();
  const { data: session } = useSession();
  const { grandTotal, appliedDiscount, clearCart } = usePosCart();
  const checkout = usePosCheckout();

  const [pending, setPending] = useState<PendingCheckout | null>(null);
  const [result, setResult] = useState<CheckoutResponse | null>(null);
  const [txnDetail, setTxnDetail] = useState<TransactionDetailResponse | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [invoiceOpen, setInvoiceOpen] = useState(false);

  // Read pending checkout info set by terminal page
  useEffect(() => {
    const stored = localStorage.getItem("pos:pending_checkout");
    if (stored) {
      try {
        setPending(JSON.parse(stored) as PendingCheckout);
      } catch {
        router.push("/terminal");
      }
    } else {
      router.push("/terminal");
    }
  }, [router]);

  // Auto-process when we have pending checkout info
  useEffect(() => {
    if (!pending || result) return;
    processCheckout(pending.method);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pending]);

  async function processCheckout(method: PaymentMethod) {
    if (!pending || isProcessing) return;
    setIsProcessing(true);

    try {
      const checkoutResult = await checkout.checkout(pending.transactionId, {
        payment_method: method,
        applied_discount: appliedDiscount
          ? { source: appliedDiscount.source, ref: appliedDiscount.ref }
          : undefined,
        insurance_no:
          method === "insurance" && pending.insuranceNo
            ? pending.insuranceNo
            : undefined,
      });

      // Fetch full transaction with items for receipt
      const detail = await fetchAPI<TransactionDetailResponse>(
        `/api/v1/pos/transactions/${pending.transactionId}`,
      );

      setResult(checkoutResult);
      setTxnDetail(detail);
      // Auto-open the A4 invoice on successful commit (per design handoff).
      // Cashier can Esc/close to return to the thermal receipt view.
      setInvoiceOpen(true);
      localStorage.removeItem("pos:pending_checkout");
    } catch {
      // Error shown in UI
      setIsProcessing(false);
    }
  }

  async function handleEmail() {
    if (!result) return;
    try {
      await postAPI(`/api/v1/pos/receipts/${result.transaction.id}/email`, {
        email: "customer@example.com",
      });
    } catch {
      // Ignore email errors for now
    }
  }

  function handleNewSale() {
    clearCart();
    localStorage.removeItem("pos:pending_checkout");
    localStorage.removeItem("pos:active_transaction");
    router.push("/terminal");
  }

  // Loading state while processing
  if (isProcessing && !result) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4">
        <Loader2 className="h-10 w-10 animate-spin text-accent" />
        <p className="text-sm text-text-secondary">Processing payment…</p>
      </div>
    );
  }

  // Error state
  if (checkout.error) {
    return (
      <div className="flex min-h-screen flex-col">
        <header className="flex h-14 items-center border-b border-border bg-surface px-4">
          <button
            type="button"
            onClick={() => router.back()}
            className="flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </button>
        </header>
        <main className="flex flex-1 flex-col items-center justify-center gap-4 p-4">
          <p className="text-base font-medium text-destructive">Checkout Failed</p>
          <p className="text-sm text-text-secondary">{checkout.error}</p>
          <button
            type="button"
            onClick={() => router.back()}
            className="rounded-xl bg-accent px-6 py-3 text-sm font-semibold text-accent-foreground"
          >
            Try Again
          </button>
        </main>
      </div>
    );
  }

  // Success state
  if (result && txnDetail) {
    const cashierName =
      (session?.user?.name as string | undefined) ?? "Cashier";
    const discountSource = appliedDiscount?.source;
    return (
      <div className="flex min-h-screen flex-col">
        <header className="flex h-14 items-center justify-between border-b border-border bg-surface px-4">
          <OfflineBadge />
          <span className="text-sm font-semibold text-text-primary">Checkout Complete</span>
          <button
            type="button"
            onClick={() => setInvoiceOpen(true)}
            data-testid="pos-checkout-view-invoice"
            className={cn(
              "flex items-center gap-2 rounded-lg border border-border px-3 py-1.5",
              "text-xs font-medium text-text-secondary hover:bg-surface-raised",
            )}
          >
            <FileText className="h-3.5 w-3.5" />
            A4 invoice
          </button>
        </header>
        <main className="flex flex-1 items-center justify-center p-4">
          <ReceiptPreview
            transaction={txnDetail}
            checkoutResult={result}
            onEmail={handleEmail}
            onClose={handleNewSale}
          />
        </main>
        <InvoiceModal
          open={invoiceOpen}
          onClose={() => setInvoiceOpen(false)}
          transaction={txnDetail}
          checkoutResult={result}
          branchName={INVOICE_BRANCH_NAME}
          branchAddress={INVOICE_BRANCH_ADDRESS}
          taxNumber={INVOICE_TAX_NUMBER}
          cashierName={cashierName}
          voucher={discountSource === "voucher" ? appliedDiscount?.ref : null}
          promotion={discountSource === "promotion" ? appliedDiscount?.label : null}
        />
      </div>
    );
  }

  // Fallback: manual payment selection (if auto-process skipped)
  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex h-14 items-center border-b border-border bg-surface px-4">
        <button
          type="button"
          onClick={() => router.back()}
          className="flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>
      </header>
      <main className={cn("flex flex-1 flex-col items-center justify-center p-6", "max-w-sm mx-auto w-full")}>
        <PaymentPanel
          grandTotal={grandTotal}
          onCheckout={processCheckout}
        />
      </main>
    </div>
  );
}
