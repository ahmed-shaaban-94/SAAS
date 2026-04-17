"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { X, Clock } from "lucide-react";
import { ProductSearch } from "@/components/pos/ProductSearch";
import { CartPanel } from "@/components/pos/CartPanel";
import { PaymentPanel } from "@/components/pos/PaymentPanel";
import { NumPad } from "@/components/pos/NumPad";
import { PharmacistVerification } from "@/components/pos/PharmacistVerification";
import { OfflineBadge } from "@/components/pos/OfflineBadge";
import { usePosCart } from "@/hooks/use-pos-cart";
import { usePosCheckout } from "@/hooks/use-pos-checkout";
import { cn } from "@/lib/utils";
import type { PosProductResult, PaymentMethod, TerminalSessionResponse } from "@/types/pos";

// ---- Terminal guard ----
// In a full implementation this reads from localStorage / session.
// The terminal is set when the cashier "opens" a terminal on the shift page.
function useActiveTerminal(): TerminalSessionResponse | null {
  const [terminal, setTerminal] = useState<TerminalSessionResponse | null>(null);
  useEffect(() => {
    const stored = localStorage.getItem("pos:active_terminal");
    if (stored) {
      try {
        setTerminal(JSON.parse(stored) as TerminalSessionResponse);
      } catch {
        // Corrupt storage — ignore
      }
    }
  }, []);
  return terminal;
}

export default function PosTerminalPage() {
  const router = useRouter();
  const terminal = useActiveTerminal();
  const { items, grandTotal, hasControlledSubstance, addItem } = usePosCart();
  const checkout = usePosCheckout();

  const [numpadValue, setNumpadValue] = useState("");
  const [pharmacistOpen, setPharmacistOpen] = useState(false);
  const [pendingDrug, setPendingDrug] = useState<PosProductResult | null>(null);
  const [activeTransactionId, setActiveTransactionId] = useState<number | null>(null);

  // If no terminal open, redirect to shift page
  useEffect(() => {
    if (terminal === null) {
      const timer = setTimeout(() => router.push("/shift"), 800);
      return () => clearTimeout(timer);
    }
  }, [terminal, router]);

  // F2: trigger checkout
  useEffect(() => {
    const handler = () => { if (grandTotal > 0) router.push("/checkout"); };
    window.addEventListener("pos:open-checkout", handler);
    return () => window.removeEventListener("pos:open-checkout", handler);
  }, [grandTotal, router]);

  // F8: return
  useEffect(() => {
    const handler = () => router.push("/history");
    window.addEventListener("pos:open-return", handler);
    return () => window.removeEventListener("pos:open-return", handler);
  }, [router]);

  function handleProductSelect(drug: PosProductResult) {
    if (drug.is_controlled) {
      setPendingDrug(drug);
      setPharmacistOpen(true);
      return;
    }
    addDrugToCart(drug, null);
  }

  function addDrugToCart(drug: PosProductResult, pharmacistId: string | null) {
    addItem({
      drug_code: drug.drug_code,
      drug_name: drug.drug_name,
      batch_number: null,
      expiry_date: null,
      quantity: 1,
      unit_price: drug.unit_price,
      discount: 0,
      line_total: drug.unit_price,
      is_controlled: drug.is_controlled,
    });
  }

  async function handleCheckout(method: PaymentMethod) {
    if (!terminal || items.length === 0) return;

    try {
      // Create a new server transaction if we don't have one yet
      let txnId = activeTransactionId;
      if (!txnId) {
        const txn = await checkout.createTransaction({
          terminal_id: terminal.id,
          site_code: terminal.site_code,
        });
        txnId = txn.id;
        setActiveTransactionId(txnId);
      }

      // Store transaction + method for checkout page
      localStorage.setItem("pos:pending_checkout", JSON.stringify({ transactionId: txnId, method }));
      router.push("/checkout");
    } catch {
      // Error shown via checkout.error state
    }
  }

  if (!terminal) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center text-text-secondary">
          <p className="text-sm">No terminal open. Redirecting to shift…</p>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Header */}
      <header className="flex h-14 items-center justify-between border-b border-border bg-surface px-4">
        <div className="flex items-center gap-3">
          <OfflineBadge />
          <span className="text-sm font-semibold text-text-primary">DataPulse POS</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-text-secondary">
            <Clock className="h-3.5 w-3.5" />
            <span>{terminal.terminal_name}</span>
          </div>
          <button
            type="button"
            onClick={() => router.push("/shift")}
            className={cn(
              "flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5",
              "text-xs font-medium text-text-secondary hover:bg-surface-raised",
            )}
          >
            <X className="h-3.5 w-3.5" />
            Close
          </button>
        </div>
      </header>

      {/* Main split layout */}
      <main className="flex flex-1 overflow-hidden">
        {/* Left panel: search + numpad (60%) */}
        <div className="flex w-[60%] flex-col gap-3 overflow-hidden border-r border-border p-4">
          <ProductSearch
            siteCode={terminal.site_code}
            onSelect={handleProductSelect}
            className="flex-1"
          />
          <NumPad
            value={numpadValue}
            onChange={setNumpadValue}
            onSubmit={(val) => {
              // Quantity input: apply to last cart item
              window.dispatchEvent(new CustomEvent("pos:numpad-qty", { detail: val }));
              setNumpadValue("");
            }}
          />
          {checkout.error && (
            <p className="text-center text-xs text-destructive">{checkout.error}</p>
          )}
        </div>

        {/* Right panel: cart + totals + payment (40%) */}
        <div className="flex w-[40%] flex-col gap-3 overflow-hidden p-4">
          <CartPanel className="flex-1 overflow-hidden" />
          <PaymentPanel
            grandTotal={grandTotal}
            disabled={checkout.isLoading || items.length === 0}
            onCheckout={handleCheckout}
          />
        </div>
      </main>

      {/* Pharmacist verification modal */}
      <PharmacistVerification
        open={pharmacistOpen}
        drugCode={pendingDrug?.drug_code ?? ""}
        onVerified={(pharmacistId) => {
          setPharmacistOpen(false);
          if (pendingDrug) addDrugToCart(pendingDrug, pharmacistId);
          setPendingDrug(null);
        }}
        onCancel={() => {
          setPharmacistOpen(false);
          setPendingDrug(null);
        }}
      />
    </>
  );
}
