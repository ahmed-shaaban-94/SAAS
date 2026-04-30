"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { TopStatusStrip } from "@/components/pos/terminal/TopStatusStrip";
import { useActiveShift } from "@/hooks/use-active-shift";
import { PharmacistVerification } from "@/components/pos/PharmacistVerification";
import { VoucherCodeModal } from "@/components/pos/VoucherCodeModal";
import {
  InsuranceModal,
  type InsuranceApplyPayload,
} from "@/components/pos/InsuranceModal";
import { ScanBar } from "@/components/pos/terminal/ScanBar";
import { QuickPickGrid } from "@/components/pos/terminal/QuickPickGrid";
import { CartTable } from "@/components/pos/terminal/CartTable";
import { OrderTabs } from "@/components/pos/terminal/OrderTabs";
import { TotalsHero } from "@/components/pos/terminal/TotalsHero";
import { ShortcutLegend } from "@/components/pos/terminal/ShortcutLegend";
import { ShortcutsCheatSheet } from "@/components/pos/ShortcutsCheatSheet";
// ActivePaymentStrip owns the InsuranceState shape — we still import the
// type for local state, but the component itself renders inside the
// CheckoutConfirmModal now (D0). Same for Keypad, PaymentTiles,
// ChargeButton — those are all re-composed inside the modal.
import { type InsuranceState } from "@/components/pos/terminal/ActivePaymentStrip";
import { ScanToast } from "@/components/pos/terminal/ScanToast";
import { ScanDisambigPicker } from "@/components/pos/terminal/ScanDisambigPicker";
import { ProvisionalBanner } from "@/components/pos/terminal/ProvisionalBanner";
import { productToQuickPick, type TilePaymentMethod } from "@/components/pos/terminal/types";
import { CheckoutConfirmModal } from "@/components/pos/terminal/CheckoutConfirmModal";
import { ClinicalPanel } from "@/components/pos/terminal/ClinicalPanel";
import { CustomerBar } from "@/components/pos/terminal/CustomerBar";
import { ChurnAlertCard } from "@/components/pos/terminal/ChurnAlertCard";
import { ShiftOpenModal } from "@/components/pos/terminal/ShiftOpenModal";
import { ManagerPinOverrideModal } from "@/components/pos/terminal/ManagerPinOverrideModal";
import { usePosCustomerLookup } from "@/hooks/use-pos-customer-lookup";
import { useManagerOverride } from "@/hooks/use-manager-override";
import { usePosCart } from "@/hooks/use-pos-cart";
import { usePosCheckout } from "@/hooks/use-pos-checkout";
import { usePosProducts } from "@/hooks/use-pos-products";
import { useOfflineState } from "@/hooks/use-offline-state";
import { cn } from "@/lib/utils";
import type { PosProductResult, TerminalSessionResponse } from "@/types/pos";
import { computeVoucherDiscount, type CartVoucher } from "@/contexts/pos-cart-context";
import { fmtEgp } from "@/components/pos/terminal/types";

// ---- Terminal guard ----
function useActiveTerminal(): [TerminalSessionResponse | null, (s: TerminalSessionResponse) => void] {
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
  // Wrap setter to narrow the type: callers only ever pass a full session object.
  const updateTerminal = (s: TerminalSessionResponse) => setTerminal(s);
  return [terminal, updateTerminal];
}

export default function PosTerminalPage() {
  const router = useRouter();
  const [terminal, setTerminal] = useActiveTerminal();
  const { overrideOpen, overrideLabel, requestOverride, approveOverride, cancelOverride } =
    useManagerOverride();
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
  const { shift } = useActiveShift(terminal?.id);

  // Voucher presentation derived from the unified cart-discount slot. Promotions
  // live in the same slot but render through a different UI (PromotionsModal +
  // CartPanel pill) — these two vars only light up for voucher-sourced discounts.
  const voucherCode =
    appliedDiscount?.source === "voucher" ? appliedDiscount.ref : null;

  // UI state — declared early so the catalog SWR can drive off scanQuery.
  const [scanQuery, setScanQuery] = useState("");

  // Catalog SWR drives both the Quick Pick tiles AND handleScanSubmit's
  // exact-match lookup. When the cashier is actively typing (2+ chars),
  // we hit /pos/products/search?q={typed} so any code/name they enter
  // resolves against live API results — previously the lookup only
  // searched a hardcoded "ab" prefetch and would silently "no-match"
  // anything outside that 20-row slice. When the scan bar is idle
  // (empty), we fall back to the seed query so QuickPick stays useful.
  const { products: catalog, isLoading: isCatalogLoading } = usePosProducts({
    query: scanQuery.trim().length >= 2 ? scanQuery.trim() : terminal ? "ab" : "",
    siteCode: terminal?.site_code ?? "",
  });
  const quickPick = useMemo(() => catalog.slice(0, 9).map(productToQuickPick), [catalog]);
  const [scanToast, setScanToast] = useState<string | null>(null);
  // Increments on every successful add — drives the scan-flash overlay.
  const [scanFlashKey, setScanFlashKey] = useState(0);
  // Independent counter — drives the red rejection-flash overlay.
  const [scanErrorFlashKey, setScanErrorFlashKey] = useState(0);
  const [activePayment, setActivePayment] = useState<TilePaymentMethod>("cash");
  const [cashTendered, setCashTendered] = useState("");
  const [cardLast4, setCardLast4] = useState("");
  const [insurance, setInsurance] = useState<InsuranceState | null>(null);
  const [insuranceNumber, setInsuranceNumber] = useState<string | null>(null);
  const [voucherOpen, setVoucherOpen] = useState(false);
  const [insuranceOpen, setInsuranceOpen] = useState(false);
  const [pharmacistOpen, setPharmacistOpen] = useState(false);
  // D0 — v9 design: the payment stack (tiles + strip + keypad + charge)
  // lives inside a confirm modal, not inline on the right column. This
  // frees the right column for the Clinical/AI panel in Phase D1.
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [cheatSheetOpen, setCheatSheetOpen] = useState(false);
  // D3 — customer phone lookup. Currently backed by fixtures (issue
  // #624 for the real endpoint). Phone state lives here so the churn
  // alert below CustomerBar and any future D4 loyalty surfaces can
  // read the same resolved customer without re-fetching.
  const [customerPhone, setCustomerPhone] = useState("");
  const { data: resolvedCustomer, isLoading: isCustomerLoading } =
    usePosCustomerLookup(customerPhone);
  const [pendingDrug, setPendingDrug] = useState<PosProductResult | null>(null);
  const [lastKeypadKey, setLastKeypadKey] = useState<string | null>(null);
  const [unsyncedCodes, setUnsyncedCodes] = useState<Set<string>>(() => new Set());
  const [activeTransactionId, setActiveTransactionId] = useState<number | null>(null);
  // When a scan query matches >1 product by substring, show a picker
  // instead of silently landing on the first hit. Audit §4.2 click-path.
  const [disambigCandidates, setDisambigCandidates] = useState<
    ReturnType<typeof productToQuickPick>[] | null
  >(null);

  const scanInputRef = useRef<HTMLInputElement>(null);

  // D2 — active drug code for ClinicalPanel: track the most-recently-added
  // item so the panel auto-updates as the cashier scans or quick-picks.
  const [activeDrugCode, setActiveDrugCode] = useState<string | null>(null);

  // No redirect — ShiftOpenModal blocks the page until a shift is opened.

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
      setActiveDrugCode(item.drug_code);
      setScanToast(`${item.drug_name} added`);
      setScanFlashKey((k) => k + 1);
      // Refocus scan bar
      scanInputRef.current?.focus();
    },
    [addItem, catalog, offline.isOnline],
  );

  const handleScanSubmit = useCallback(
    (value: string) => {
      const q = value.trim();
      if (!q) return;
      const qLower = q.toLowerCase();
      const qUpper = q.toUpperCase();

      // Exact SKU match always wins — no ambiguity possible, no picker.
      const skuHit = catalog.find((p) => p.drug_code.toUpperCase() === qUpper);
      if (skuHit) {
        addQuickPick(productToQuickPick(skuHit));
        setScanQuery("");
        return;
      }

      // Substring match against drug_name OR drug_code (case-insensitive).
      const nameHits = catalog.filter(
        (p) =>
          p.drug_name.toLowerCase().includes(qLower) ||
          p.drug_code.toLowerCase().includes(qLower),
      );
      if (nameHits.length === 0) {
        setScanToast(`No match for "${q}"`);
        setScanErrorFlashKey((k) => k + 1);
        return;
      }
      if (nameHits.length === 1) {
        addQuickPick(productToQuickPick(nameHits[0]));
        setScanQuery("");
        return;
      }
      // 2+ matches — let the cashier disambiguate instead of guessing.
      setDisambigCandidates(nameHits.slice(0, 3).map(productToQuickPick));
    },
    [catalog, addQuickPick],
  );

  const handleDisambigPick = useCallback(
    (tile: ReturnType<typeof productToQuickPick>) => {
      setDisambigCandidates(null);
      setScanQuery("");
      addQuickPick(tile);
    },
    [addQuickPick],
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
      if (!item) return;
      const next = item.quantity - 1;
      // Decrementing to zero is functionally a remove and must go through
      // the same manager-PIN gate, otherwise a cashier could side-step the
      // override by clicking Minus instead of the X button.
      if (next <= 0) {
        requestOverride("حذف صنف من السلة", () => {
          removeItem(drugCode);
          setUnsyncedCodes((prev) => {
            const updated = new Set(prev);
            updated.delete(drugCode);
            return updated;
          });
        });
        return;
      }
      updateQuantity(drugCode, next);
    },
    [items, updateQuantity, removeItem, requestOverride],
  );

  const handleRemove = useCallback(
    (drugCode: string) => {
      requestOverride("حذف صنف من السلة", () => {
        removeItem(drugCode);
        setUnsyncedCodes((prev) => {
          const next = new Set(prev);
          next.delete(drugCode);
          return next;
        });
      });
    },
    [removeItem, requestOverride],
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
      // F12 → Start Checkout. Only fires when no modal is open, the
      // cart is chargeable, and focus isn't trapped in an input.
      if (e.key === "F12") {
        const anyModalOpen =
          checkoutOpen ||
          voucherOpen ||
          insuranceOpen ||
          pharmacistOpen ||
          cheatSheetOpen;
        const canCharge =
          items.length > 0 && grandTotal > 0 && !checkout.isLoading;
        if (!anyModalOpen && canCharge && !isInput) {
          e.preventDefault();
          setCheckoutOpen(true);
          return;
        }
      }
      if (e.key === "Escape" && voucherOpen) {
        // VoucherCodeModal handles its own Escape
        return;
      }

      if (!isInput) {
        if (e.key === "?") {
          e.preventDefault();
          setCheatSheetOpen((v) => !v);
          return;
        }
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
        if (
          e.key === "Enter" &&
          items.length > 0 &&
          grandTotal > 0 &&
          !checkoutOpen
        ) {
          // D0 — first Enter opens the confirm modal; second Enter
          // (intercepted inside the modal) actually charges. This splits
          // the "review" and "commit" gestures that used to collapse
          // into a single keystroke.
          e.preventDefault();
          setCheckoutOpen(true);
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
    checkoutOpen,
    cheatSheetOpen,
    setCheatSheetOpen,
    insuranceOpen,
    pharmacistOpen,
    checkout.isLoading,
  ]);

  // Hijack the legacy F2 layout shortcut (now = Sync).
  useEffect(() => {
    const redirect = () => router.push("/sync-issues");
    window.addEventListener("pos:open-checkout", redirect);
    return () => window.removeEventListener("pos:open-checkout", redirect);
  }, [router]);

  // ---- Render ----

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
      {/* D4 — TopStatusStrip (sync pill · commission · daily target · clock) */}
      <TopStatusStrip
        shift={shift}
        terminalName={terminal?.terminal_name}
        onClose={() => router.push("/shift")}
      />

      {isOffline && <ProvisionalBanner pending={offline.pending} />}

      {/* D1 — three-column layout (v9 handoff §1.3, 4fr / 3fr / 2.5fr).
          Responsive cascade:
          - ≥1280px (xl): 3-col — Cart · Quick catalog · Clinical
          - 1024–1280px (lg): 2-col — Cart·Catalog on one row, Clinical below
          - <1024px: single column stack
       */}
      <main
        className={cn(
          "relative grid flex-1 gap-3.5 overflow-hidden p-3.5",
          "grid-cols-1",
          "lg:grid-cols-[minmax(0,1.45fr)_minmax(0,1fr)] lg:grid-rows-[minmax(0,1fr)_minmax(0,auto)]",
          "xl:grid-cols-[minmax(0,4fr)_minmax(0,3fr)_minmax(0,2.5fr)] xl:grid-rows-1",
        )}
      >
        {/* Ambient indigo+purple glow halos — Gemini POV port (2026-04-30). */}
        <div className="pos-glow-halo" aria-hidden="true" />
        {/* COL 1 — Cart column (handoff §1.3: customer bar → churn alert →
            scan → cart list → cart foot with grand total + CTA). D3 adds
            the customer bar and churn card above the scan bar;
            ChurnAlertCard is conditional per §Editorial Principles #4
            ("AI triggers, not AI chatter"). */}
        <section
          aria-label="Cart column"
          className={cn(
            "relative z-[1] flex min-w-0 flex-col gap-3 overflow-hidden",
            "lg:row-start-1 lg:col-start-1",
            "xl:col-start-1",
          )}
        >
          <OrderTabs orderName="طلب #101" itemCount={itemCount} />
          <CustomerBar
            phone={customerPhone}
            onPhoneChange={setCustomerPhone}
            customer={resolvedCustomer}
            isLoading={isCustomerLoading}
            onSubmit={() => scanInputRef.current?.focus()}
          />
          {resolvedCustomer?.churn && (
            <ChurnAlertCard churn={resolvedCustomer.churn} />
          )}
          <ScanBar
            ref={scanInputRef}
            value={scanQuery}
            onChange={setScanQuery}
            onSubmit={handleScanSubmit}
            isOnline={!isOffline}
            flashKey={scanFlashKey}
            errorFlashKey={scanErrorFlashKey}
          />
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <CartTable
              items={items}
              unsyncedCodes={unsyncedCodes}
              itemCount={itemCount}
              averageItem={averageItem}
              onIncrement={handleIncrement}
              onDecrement={handleDecrement}
              onRemove={handleRemove}
            />
          </div>

          {/* Cart foot — handoff §1.3 "sticky bottom": totals hero + Start
              Checkout CTA. Always visible above the fold. */}
          <div className="flex flex-col gap-3 border-t border-[var(--pos-line)] pt-3">
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
            <button
              type="button"
              onClick={() => setCheckoutOpen(true)}
              disabled={chargeDisabled}
              aria-label={`Start checkout for EGP ${fmtEgp(grandTotal)} (Enter)`}
              data-testid="start-checkout-button"
              className={cn(
                "grid items-center gap-3 rounded-xl px-5 py-4 transition-all duration-200",
                "[grid-template-columns:auto_1fr_auto]",
                chargeDisabled
                  ? "cursor-not-allowed border border-[var(--pos-line)] bg-white/[0.04] text-[var(--pos-ink-2)]"
                  : cn(
                      "cursor-pointer border-0 text-[#021018]",
                      "bg-gradient-to-b from-[#5cdfff] to-[#00a6cc]",
                      "shadow-[0_0_24px_rgba(0,199,242,0.4),0_6px_16px_rgba(0,199,242,0.25),inset_0_1px_0_rgba(255,255,255,0.35)]",
                      "hover:from-[#6be5ff] hover:to-[#00b5dd]",
                    ),
              )}
            >
              <span className="text-[18px] font-bold">Start Checkout</span>
              <span className="text-center font-mono text-[22px] font-bold tabular-nums">
                EGP {fmtEgp(grandTotal)}
              </span>
              <kbd
                className={cn(
                  "rounded border px-2 py-0.5 font-mono text-[10px] font-semibold",
                  chargeDisabled
                    ? "border-[var(--pos-line)] bg-white/[0.04] text-[var(--pos-ink-3)]"
                    : "border-[rgba(2,16,24,0.3)] bg-[rgba(2,16,24,0.22)] text-[#021018]",
                )}
              >
                Enter ↵
              </kbd>
            </button>
          </div>
        </section>

        {/* COL 2 — Quick catalog column. D6 will rebuild QuickPickGrid per
            handoff (category accents, bonus stars, expiry meta, tactile
            press animation). D1 just relocates it to its final home. */}
        <section
          aria-label="Quick catalog column"
          className={cn(
            "relative z-[1] flex min-w-0 flex-col gap-3 overflow-hidden",
            "lg:row-start-1 lg:col-start-2",
            "xl:col-start-2",
          )}
        >
          <ShortcutLegend />
          <QuickPickGrid
            items={quickPick}
            onPick={addQuickPick}
            loading={isCatalogLoading && quickPick.length === 0}
          />
        </section>

        {/* COL 3 — Clinical / AI column. D1 renders a skeleton only;
            D2 replaces with the real ClinicalPanel wired to an
            `activeDrugCode` derived from the cart. */}
        <section
          aria-label="Clinical and AI column"
          className={cn(
            "relative z-[1] flex min-w-0 flex-col overflow-hidden",
            "lg:col-span-2 lg:row-start-2",
            "xl:col-start-3 xl:col-span-1 xl:row-start-1",
          )}
        >
          <ClinicalPanel activeDrugCode={activeDrugCode} />
        </section>
      </main>

      {/* Toasts + modals */}
      <ScanToast message={scanToast} onDismiss={() => setScanToast(null)} />
      <ScanDisambigPicker
        candidates={disambigCandidates ?? []}
        onPick={handleDisambigPick}
        onCancel={() => setDisambigCandidates(null)}
      />
      {/* D0 — confirm-step checkout modal. Rendered before the voucher
          and insurance modals so those two can layer on top when opened
          from within the checkout flow. */}
      <CheckoutConfirmModal
        open={checkoutOpen}
        itemCount={itemCount}
        grandTotal={grandTotal}
        activePayment={activePayment}
        onActivePaymentChange={(m) => {
          setActivePayment(m);
          if (m === "voucher" && !voucherCode) setVoucherOpen(true);
        }}
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
        lastKeypadKey={lastKeypadKey}
        chargeDisabled={chargeDisabled}
        onCharge={handleCheckout}
        onClose={() => setCheckoutOpen(false)}
        error={checkout.error ?? null}
      />
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
            setActiveDrugCode(pendingDrug.drug_code);
            setScanToast(`${pendingDrug.drug_name} added`);
          }
          setPendingDrug(null);
        }}
        onCancel={() => {
          setPharmacistOpen(false);
          setPendingDrug(null);
        }}
      />

      {/* D5 — shift-open gate (shown when there is no active terminal session) */}
      {!terminal && (
        <ShiftOpenModal
          onOpened={(session) => setTerminal(session)}
        />
      )}

      {/* D5 — manager PIN gate for destructive cart actions */}
      <ManagerPinOverrideModal
        open={overrideOpen}
        actionLabel={overrideLabel}
        onApproved={approveOverride}
        onCancel={cancelOverride}
      />

      <ShortcutsCheatSheet open={cheatSheetOpen} onClose={() => setCheatSheetOpen(false)} />
    </div>
  );
}
