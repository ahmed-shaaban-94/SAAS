"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "@/lib/auth-bridge";
import { ArrowLeft, FileText, Loader2, Printer, SkipForward } from "lucide-react";
import { PaymentPanel } from "@/components/pos/PaymentPanel";
import { InvoiceModal } from "@/components/pos/InvoiceModal";
import { OfflineBadge } from "@/components/pos/OfflineBadge";
import { SalesReceipt } from "@/components/pos/receipts/SalesReceipt";
import { InsuranceReceipt } from "@/components/pos/receipts/InsuranceReceipt";
import { DeliveryReceipt } from "@/components/pos/receipts/DeliveryReceipt";
import { usePosCart } from "@/hooks/use-pos-cart";
import { usePosCheckout } from "@/hooks/use-pos-checkout";
import { fetchAPI, postAPI } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type {
  PaymentMethod,
  CheckoutResponse,
  TransactionDetailResponse,
} from "@/types/pos";
import type { ReceiptData } from "@/components/pos/receipts/receipt-mock";

const INVOICE_BRANCH_NAME = "Maadi branch · POS-03";
const INVOICE_BRANCH_ADDRESS = "12 Sobhi Saleh St · Cairo";
const INVOICE_TAX_NUMBER = "428-893-011";

interface PendingCheckout {
  transactionId: number;
  method: PaymentMethod;
  insuranceNo?: string;
  isDelivery?: boolean;
  deliveryAddress?: string;
  deliveryRider?: string;
  deliveryRiderPhone?: string;
  deliveryEta?: number;
}

function buildReceiptData(
  txn: TransactionDetailResponse,
  result: CheckoutResponse,
  cashierName: string,
  insuranceNo?: string,
  pendingDelivery?: Pick<PendingCheckout, "deliveryAddress" | "deliveryRider" | "deliveryRiderPhone" | "deliveryEta">,
): ReceiptData {
  const ts = new Date(txn.created_at);
  const data: ReceiptData = {
    meta: {
      invoice_number: result.receipt_number ?? `TXN-${txn.id}`,
      date: ts.toLocaleDateString("ar-EG", {
        day: "numeric",
        month: "long",
        year: "numeric",
      }),
      time: ts.toLocaleTimeString("ar-EG", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }),
      shift_id: "",
      cashier_name: cashierName,
      site_name_ar: txn.site_code,
    },
    customer: {
      name_ar: txn.customer_id ?? "",
    },
    items: txn.items.map((i) => ({
      drug_name: i.drug_name,
      drug_name_ar: i.drug_name,
      quantity: i.quantity,
      unit_price: i.unit_price,
      line_total: i.line_total,
      batch_number: i.batch_number ?? undefined,
    })),
    totals: {
      subtotal: txn.subtotal,
      discount: txn.discount_total,
      vat: txn.tax_total,
      grand_total: txn.grand_total,
      payment_method: txn.payment_method ?? "",
    },
  };

  if (txn.payment_method === "insurance" && insuranceNo) {
    data.insurance = {
      company_name: "Insurance",
      plan_name: insuranceNo,
      approval_code: insuranceNo,
      auth_time: ts.toLocaleTimeString("ar-EG"),
      insurer_pct: 0,
      insurer_amount: 0,
      patient_pct: 100,
      patient_amount: txn.grand_total,
    };
  }

  if (pendingDelivery?.deliveryAddress) {
    data.delivery = {
      address: pendingDelivery.deliveryAddress,
      rider_name: pendingDelivery.deliveryRider ?? "",
      rider_phone: pendingDelivery.deliveryRiderPhone ?? "",
      eta_minutes: pendingDelivery.deliveryEta ?? 30,
    };
  }

  return data;
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
  const printedRef = useRef(false);

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

  useEffect(() => {
    if (!pending || result) return;
    processCheckout(pending.method);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pending]);

  // Auto-print on first success — 300ms DOM-settle delay
  useEffect(() => {
    if (!result || printedRef.current) return;
    printedRef.current = true;
    const id = setTimeout(() => window.print(), 300);
    return () => clearTimeout(id);
  }, [result]);

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
          method === "insurance" && pending.insuranceNo ? pending.insuranceNo : undefined,
      });

      const detail = await fetchAPI<TransactionDetailResponse>(
        `/api/v1/pos/transactions/${pending.transactionId}`,
      );

      setResult(checkoutResult);
      setTxnDetail(detail);
      localStorage.removeItem("pos:pending_checkout");
    } catch {
      setIsProcessing(false);
    }
  }

  const handlePrint = useCallback(() => window.print(), []);

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

  if (isProcessing && !result) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4">
        <Loader2 className="h-10 w-10 animate-spin text-accent" />
        <p className="text-sm text-text-secondary">Processing payment…</p>
      </div>
    );
  }

  if (checkout.error) {
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

  if (result && txnDetail) {
    const cashierName = (session?.user?.name as string | undefined) ?? "Cashier";
    const discountSource = appliedDiscount?.source;
    const receiptData = buildReceiptData(
      txnDetail,
      result,
      cashierName,
      pending?.insuranceNo,
      pending ?? undefined,
    );
    const isInsurance = txnDetail.payment_method === "insurance";
    const isDelivery = pending?.isDelivery === true;

    return (
      <div className="pos-root flex min-h-screen flex-col">
        {/* Header — hidden on print via data-no-print */}
        <header
          data-no-print="true"
          className="flex h-14 items-center justify-between border-b border-[var(--pos-line)] bg-[var(--pos-card)] px-4"
        >
          <OfflineBadge />
          <div className="flex flex-col items-center">
            <span
              className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-emerald-300"
              aria-hidden="true"
            >
              ● Charged
            </span>
            <span className="font-[family-name:var(--font-fraunces)] text-sm italic text-text-primary">
              Pick a receipt, or move on
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setInvoiceOpen(true)}
              data-testid="pos-checkout-view-invoice"
              className={cn(
                "flex items-center gap-2 rounded-lg border border-[var(--pos-line)] px-3 py-1.5",
                "text-xs font-medium text-text-secondary hover:border-cyan-400/40 hover:bg-cyan-400/5",
              )}
            >
              <FileText className="h-3.5 w-3.5" />
              A4 invoice
            </button>
            <button
              type="button"
              onClick={handlePrint}
              data-testid="pos-checkout-reprint"
              className={cn(
                "flex items-center gap-2 rounded-lg border border-[var(--pos-line)] px-3 py-1.5",
                "text-xs font-medium text-text-secondary hover:border-cyan-400/40 hover:bg-cyan-400/5",
              )}
            >
              <Printer className="h-3.5 w-3.5" />
              Reprint
            </button>
            <button
              type="button"
              onClick={handleNewSale}
              data-testid="pos-checkout-skip-receipt"
              aria-label="Skip receipt and start a new sale"
              className={cn(
                "flex items-center gap-2 rounded-lg border border-amber-400/30 bg-amber-400/10 px-3 py-1.5",
                "text-xs font-medium text-amber-300 hover:bg-amber-400/15",
              )}
            >
              <SkipForward className="h-3.5 w-3.5" />
              Skip &amp; new sale
            </button>
          </div>
        </header>

        {/* Receipt — wrapped in pos-print-root so @media print isolates it */}
        <main className="flex flex-1 items-center justify-center p-4">
          <div className="pos-print-root pos-omni">
            {isInsurance ? (
              <InsuranceReceipt data={receiptData} />
            ) : isDelivery ? (
              <DeliveryReceipt data={receiptData} />
            ) : (
              <SalesReceipt data={receiptData} />
            )}
          </div>
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

  // Fallback: manual payment selection
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
      </header>
      <main
        className={cn(
          "flex flex-1 flex-col items-center justify-center p-6",
          "max-w-sm mx-auto w-full",
        )}
      >
        <PaymentPanel grandTotal={grandTotal} onCheckout={processCheckout} />
      </main>
    </div>
  );
}
