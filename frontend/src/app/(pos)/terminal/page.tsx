"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { X, Clock } from "lucide-react";
import { OfflineBadge } from "@/components/pos/OfflineBadge";
import { PharmacistVerification } from "@/components/pos/PharmacistVerification";
import { VoucherCodeModal } from "@/components/pos/VoucherCodeModal";
import {
  InsuranceModal,
  type InsuranceApplyPayload,
} from "@/components/pos/InsuranceModal";
import { ScanBar } from "@/components/pos/terminal/ScanBar";
import { QuickPickGrid } from "@/components/pos/terminal/QuickPickGrid";
import { CartTable } from "@/components/pos/terminal/CartTable";
import { TotalsHero } from "@/components/pos/terminal/TotalsHero";
import { Keypad } from "@/components/pos/terminal/Keypad";
import { ShortcutLegend } from "@/components/pos/terminal/ShortcutLegend";
import { PaymentTiles } from "@/components/pos/terminal/PaymentTiles";
import {
  ActivePaymentStrip,
  type InsuranceState,
} from "@/components/pos/terminal/ActivePaymentStrip";
import { ChargeButton } from "@/components/pos/terminal/ChargeButton";
import { ScanToast } from "@/components/pos/terminal/ScanToast";
import { ProvisionalBanner } from "@/components/pos/terminal/ProvisionalBanner";
import { productToQuickPick, type TilePaymentMethod } from "@/components/pos/terminal/types";
import { usePosCart } from "@/hooks/use-pos-cart";
import { usePosCheckout } from "@/hooks/use-pos-checkout";
import { usePosProducts } from "@/hooks/use-pos-products";
import { useOfflineState } from "@/hooks/use-offline-state";
import { cn } from "@/lib/utils";
import type { PosProductResult, TerminalSessionResponse } from "@/types/pos";
import { computeVoucherDiscount, type CartVoucher } from "@/contexts/pos-cart-context";

// ---- Terminal guard ----
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
  const {
    items,
    appliedDiscount,
    subtotal,
    discountTotal,
    voucherDiscount,
    taxTotal,
    grandTotal,
    itemCount,
    addItem,
    removeItem,
    updateQuantity,
    applyDiscount,
  } = usePosCart();
  const checkout = usePosCheckout();
  const offline = useOfflineState();

  // Voucher presentation derived from the unified cart-discount slot. Promotions
  // live in the same slot but render through a different UI (PromotionsModal +
  // CartPanel pill) — these two vars only light up for voucher-sourced discounts.
  const voucherCode =
    appliedDiscount?.source === "voucher" ? appliedDiscount.ref : null;

  // Browse catalog for Quick Pick (top 9). usePosProducts only fires when
  // query.length >= 2, so we use a broad two-letter seed ("ab") so the
  // search endpoint returns *some* products — when a Favorites API lands
  // this will switch to `/pos/terminals/{id}/favorites`.
  const { products: catalog } = usePosProducts({
    query: terminal ? "ab" : "",
    siteCode: terminal?.site_code ?? "",
  });
  const quickPick = useMemo(() => catalog.slice(0, 9).map(productToQuickPick), [catalog]);

  // UI state
  const [scanQuery, setScanQuery] = useState("");
  const [scanToast, setScanToast] = useState<string | null>(null);
  const [activePayment, setActivePayment] = useState<TilePaymentMethod>("cash");
  const [cashTendered, setCashTendered] = useState("");
  const [cardLast4, setCardLast4] = useState("");
  const [insurance, setInsurance] = useState<InsuranceState | null>(null);
  const [insuranceNumber, setInsuranceNumber] = useState<string | null>(null);
  const [voucherOpen, setVoucherOpen] = useState(false);
  const [insuranceOpen, setInsuranceOpen] = useState(false);
  const [pharmacistOpen, setPharmacistOpen] = useState(false);
  const [pendingDrug, setPendingDrug] = useState<PosProductResult | null>(null);
  const [lastKeypadKey, setLastKeypadKey] = useState<string | null>(null);
  const [unsyncedCodes, setUnsyncedCodes] = useState<Set<string>>(() => new Set());
  const [activeTransactionId, setActiveTransactionId] = useState<number | null>(null);

  const scanInputRef = useRef<HTMLInputElement>(null);

  // If no terminal open, redirect to shift page
  useEffect(() => {
    if (terminal === null) {
      const timer = setTimeout(() => router.push("/shift"), 800);
      return () => clearTimeout(timer);
    }
  }, [terminal, router]);

  // Auto-focus scan bar on mount
  useEffect(() => {
    scanInputRef.current?.focus();
  }, []);

  const focusScan = useCallback(() => {
    scanInputRef.current?.focus();
  }, []);

  // ----- Cart helpers -----

  const addQuickPick = useCallback(
    (item: { drug_code: string; drug_name: string; unit_price: number; is_controlled: boolean }) => {
      if (item.is_controlled) {
        // Controlled substances still require pharmacist verification; we
        // need a PosProductResult shape for the existing verifier modal.
        const drug = catalog.find((p) => p.drug_code === item.drug_code);
        if (drug) {
          setPendingDrug(drug);
          setPharmacistOpen(true);
          return;
        }
      }
      addItem({
        drug_code: item.drug_code,
        drug_name: item.drug_name,
        batch_number: null,
        expiry_date: null,
        quantity: 1,
        unit_price: item.unit_price,
        discount: 0,
        line_total: item.unit_price,
        is_controlled: item.is_controlled,
      });
      // Stamp synced state at add time. When we're offline, the line
      // gets an amber rail + QUEUED badge until the background sync
      // promotes it. A later PR will wire real queue tracking.
      if (!offline.isOnline) {
        setUnsyncedCodes((prev) => new Set(prev).add(item.drug_code));
      }
      setScanToast(`${item.drug_name} added`);
      // Refocus scan bar
      scanInputRef.current?.focus();
    },
    [addItem, catalog, offline.isOnline],
  );

  const handleScanSubmit = useCallback(
    (value: string) => {
      const q = value.trim();
      if (!q) return;
      // Exact SKU match (product.drug_code) or name substring; fall back to first result.
      let match = catalog.find((p) => p.drug_code.toUpperCase() === q.toUpperCase());
      if (!match) match = catalog.find((p) => p.drug_name.toLowerCase().includes(q.toLowerCase()));
      if (match) {
        addQuickPick(productToQuickPick(match));
        setScanQuery("");
      }
    },
    [catalog, addQuickPick],
  );

  const handleIncrement = useCallback(
    (drugCode: string) => {
      const item = items.find((i) => i.drug_code === drugCode);
      if (item) updateQuantity(drugCode, item.quantity + 1);
    },
    [items, updateQuantity],
  );

  const handleDecrement = useCallback(
    (drugCode: string) => {
      const item = items.find((i) => i.drug_code === drugCode);
      if (item) updateQuantity(drugCode, item.quantity - 1);
    },
    [items, updateQuantity],
  );

  const handleRemove = useCallback(
    (drugCode: string) => {
      removeItem(drugCode);
      setUnsyncedCodes((prev) => {
        const next = new Set(prev);
        next.delete(drugCode);
        return next;
      });
    },
    [removeItem],
  );

  // ----- Voucher flow -----

  const openVoucherModal = useCallback(() => {
    setActivePayment("voucher");
    setVoucherOpen(true);
  }, []);

  const handleVoucherApply = useCallback(
    (v: CartVoucher) => {
      // Recompute the resolved EGP discount against the current subtotal —
      // the modal's preview amount may be stale if items were added after
      // validation. Backend re-validates canonically at commit.
      const resolved = computeVoucherDiscount(v.discount_type, v.value, subtotal);
      applyDiscount({
        source: "voucher",
        ref: v.code,
        label: v.code,
        discountAmount: resolved,
      });
      setVoucherOpen(false);
    },
    [applyDiscount, subtotal],
  );

  // ----- Checkout -----

  const handleCheckout = useCallback(async () => {
    if (!terminal || items.length === 0 || grandTotal <= 0) return;
    try {
      let txnId = activeTransactionId;
      if (!txnId) {
        const txn = await checkout.createTransaction({
          terminal_id: terminal.id,
          site_code: terminal.site_code,
        });
        txnId = txn.id;
        setActiveTransactionId(txnId);
      }
      // Hand off the active transaction + selected payment method to
      // /checkout. The applied cart discount (voucher OR promotion) is
      // already persisted in the cart context and is read from there by
      // the checkout page. Insurance extras (insurance_no) ride along so
      // the checkout page can forward them in the CheckoutRequest.
      const payload: {
        transactionId: number;
        method: TilePaymentMethod;
        insuranceNo?: string;
      } = { transactionId: txnId, method: activePayment };
      if (activePayment === "insurance" && insuranceNumber) {
        payload.insuranceNo = insuranceNumber;
      }
      localStorage.setItem("pos:pending_checkout", JSON.stringify(payload));
      router.push("/checkout");
    } catch {
      // Error surfaced via checkout.error
    }
  }, [
    terminal,
    items.length,
    grandTotal,
    activeTransactionId,
    checkout,
    activePayment,
    insuranceNumber,
    router,
  ]);

  const handleInsuranceApply = useCallback(
    (payload: InsuranceApplyPayload) => {
      setInsurance(payload.state);
      setInsuranceNumber(payload.insuranceNumber);
      setActivePayment("insurance");
    },
    [],
  );

  // ----- Keyboard shortcuts -----

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement | null;
      const isInput =
        !!target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.hasAttribute?.("data-pos-scanner-ignore"));

      if (e.key === "F7") {
        e.preventDefault();
        openVoucherModal();
        return;
      }
      if (e.key === "F9") {
        e.preventDefault();
        setActivePayment("cash");
        return;
      }
      if (e.key === "F10") {
        e.preventDefault();
        setActivePayment("card");
        return;
      }
      if (e.key === "F11") {
        e.preventDefault();
        setActivePayment("insurance");
        return;
      }
      // F12 intentionally unbound — layout previously dispatched a dead
      // pos:void-transaction event on F12 which collided with this
      // handler. Voucher stays on F7.
      if (e.key === "Escape" && voucherOpen) {
        // VoucherCodeModal handles its own Escape
        return;
      }

      if (!isInput) {
        if (e.key === "/") {
          e.preventDefault();
          focusScan();
          return;
        }
        if (/^[1-9]$/.test(e.key)) {
          const idx = parseInt(e.key, 10) - 1;
          const tile = quickPick[idx];
          if (tile) {
            e.preventDefault();
            addQuickPick(tile);
            return;
          }
        }
        if (/^[0-9.]$/.test(e.key) && activePayment === "cash") {
          // Mirror digits into the keypad when cash is active.
          setLastKeypadKey(e.key);
          setCashTendered((v) => {
            if (e.key === "." && v.includes(".")) return v;
            return v + e.key;
          });
          return;
        }
        if (e.key === "Enter" && items.length > 0 && grandTotal > 0) {
          e.preventDefault();
          handleCheckout();
          return;
        }
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [
    addQuickPick,
    focusScan,
    quickPick,
    activePayment,
    items.length,
    grandTotal,
    handleCheckout,
    openVoucherModal,
    voucherOpen,
  ]);

  // Hijack the legacy F2 layout shortcut (now = Sync).
  useEffect(() => {
    const redirect = () => router.push("/sync-issues");
    window.addEventListener("pos:open-checkout", redirect);
    return () => window.removeEventListener("pos:open-checkout", redirect);
  }, [router]);

  // ---- Render ----

  if (!terminal) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center text-text-secondary">
          <p className="text-sm">No terminal open. Redirecting to shift…</p>
        </div>
      </div>
    );
  }

  const isOffline = !offline.isOnline;
  const averageItem = itemCount > 0 ? grandTotal / itemCount : 0;
  const itemDiscountTotal = Math.max(0, discountTotal - voucherDiscount);
  const chargeDisabled = items.length === 0 || grandTotal <= 0 || checkout.isLoading;

  return (
    <div
      className={cn(
        "pos-root flex min-h-screen flex-col overflow-hidden text-text-primary",
        isOffline && "pos-provisional-rail",
      )}
    >
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

      {isOffline && <ProvisionalBanner pending={offline.pending} />}

      {/* Main two-column layout (~1.45fr / 1fr) */}
      <main
        className={cn(
          "flex flex-1 gap-3.5 overflow-hidden p-3.5",
          "grid grid-cols-[minmax(0,1.45fr)_minmax(400px,1fr)]",
        )}
      >
        {/* LEFT column */}
        <section className="flex min-w-0 flex-col gap-3 overflow-hidden">
          <ScanBar
            ref={scanInputRef}
            value={scanQuery}
            onChange={setScanQuery}
            onSubmit={handleScanSubmit}
            isOnline={!isOffline}
          />
          <QuickPickGrid items={quickPick} onPick={addQuickPick} />
          <CartTable
            items={items}
            unsyncedCodes={unsyncedCodes}
            itemCount={itemCount}
            averageItem={averageItem}
            onIncrement={handleIncrement}
            onDecrement={handleDecrement}
            onRemove={handleRemove}
          />
        </section>

        {/* RIGHT column */}
        <section className="flex min-h-0 flex-col gap-3 overflow-y-auto">
          <TotalsHero
            subtotal={subtotal}
            grandTotal={grandTotal}
            itemDiscountTotal={itemDiscountTotal}
            voucherDiscount={voucherDiscount}
            taxTotal={taxTotal}
            itemCount={itemCount}
            voucherCode={voucherCode}
            insuranceCoveragePct={insurance?.coveragePct ?? null}
          />
          <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)] gap-3">
            <Keypad
              value={cashTendered}
              onChange={setCashTendered}
              disabled={activePayment !== "cash"}
              lastKey={lastKeypadKey}
            />
            <ShortcutLegend />
          </div>
          <PaymentTiles
            active={activePayment}
            onSelect={(m) => {
              setActivePayment(m);
              if (m === "voucher" && !voucherCode) setVoucherOpen(true);
            }}
            voucherCode={voucherCode}
            voucherDiscount={voucherDiscount}
            insuranceCoveragePct={insurance?.coveragePct ?? null}
          />
          <ActivePaymentStrip
            method={activePayment}
            grandTotal={grandTotal}
            cashTendered={cashTendered}
            onCashTenderedChange={setCashTendered}
            cardLast4={cardLast4}
            onCardLast4Change={setCardLast4}
            insurance={insurance}
            onInsuranceChange={(next) => {
              setInsurance(next);
              if (!next) setInsuranceNumber(null);
            }}
            onOpenInsuranceModal={() => setInsuranceOpen(true)}
            voucherCode={voucherCode}
            voucherDiscount={voucherDiscount}
            onOpenVoucherModal={() => setVoucherOpen(true)}
          />
          <ChargeButton
            grandTotal={grandTotal}
            disabled={chargeDisabled}
            onCharge={handleCheckout}
          />
          {checkout.error && (
            <p role="alert" className="text-center text-xs text-destructive">
              {checkout.error}
            </p>
          )}
        </section>
      </main>

      {/* Toasts + modals */}
      <ScanToast message={scanToast} onDismiss={() => setScanToast(null)} />
      <VoucherCodeModal
        open={voucherOpen}
        cartSubtotal={subtotal}
        onApply={handleVoucherApply}
        onCancel={() => setVoucherOpen(false)}
      />
      <InsuranceModal
        open={insuranceOpen}
        onClose={() => setInsuranceOpen(false)}
        onApply={handleInsuranceApply}
        grandTotal={grandTotal}
        initial={insurance}
      />
      <PharmacistVerification
        open={pharmacistOpen}
        drugCode={pendingDrug?.drug_code ?? ""}
        onVerified={() => {
          setPharmacistOpen(false);
          if (pendingDrug) {
            addItem({
              drug_code: pendingDrug.drug_code,
              drug_name: pendingDrug.drug_name,
              batch_number: null,
              expiry_date: null,
              quantity: 1,
              unit_price: pendingDrug.unit_price,
              discount: 0,
              line_total: pendingDrug.unit_price,
              is_controlled: pendingDrug.is_controlled,
            });
            setScanToast(`${pendingDrug.drug_name} added`);
          }
          setPendingDrug(null);
        }}
        onCancel={() => {
          setPharmacistOpen(false);
          setPendingDrug(null);
        }}
      />
    </div>
  );
}
