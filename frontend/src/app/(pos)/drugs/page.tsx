"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { X, Clock } from "lucide-react";
import { OfflineBadge } from "@/components/pos/OfflineBadge";
import { DrugsSearchBar } from "@/components/pos/drugs/DrugsSearchBar";
import { DrugsTable } from "@/components/pos/drugs/DrugsTable";
import { InventorySummary } from "@/components/pos/drugs/InventorySummary";
import { FocusedDrug } from "@/components/pos/drugs/FocusedDrug";
import { CartGoTo } from "@/components/pos/drugs/CartGoTo";
import { StocktakingModal } from "@/components/pos/StocktakingModal";
import { toDrugRow, type RxFilter, type SortKey, type SortState, type StockFilter } from "@/components/pos/drugs/types";
import { usePosCart } from "@/hooks/use-pos-cart";
import { useDrugSearch } from "@/hooks/use-drug-search";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";
import type { TerminalSessionResponse } from "@/types/pos";
import { usePosBranding } from "@/hooks/use-pos-branding";

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

export default function PosDrugsPage() {
  const router = useRouter();
  const terminal = useActiveTerminal();
  const { branding: posBranding } = usePosBranding();
  const { addItem, grandTotal, itemCount } = usePosCart();
  const toast = useToast();

  const [query, setQuery] = useState("");
  const [stockFilter, setStockFilter] = useState<StockFilter>("all");
  const [rxFilter, setRxFilter] = useState<RxFilter>("all");
  const [sort, setSort] = useState<SortState>({ key: "drug_name", dir: "asc" });
  const [qtyMap, setQtyMap] = useState<Record<string, number>>({});
  const [activeIdx, setActiveIdx] = useState(0);
  const [stocktakingOpen, setStocktakingOpen] = useState(false);

  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    searchRef.current?.focus();
  }, []);

  const { products } = useDrugSearch(query, terminal?.site_code ?? "");

  const allRows = useMemo(() => products.map(toDrugRow), [products]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const out = allRows.filter((r) => {
      if (stockFilter === "low" && r.stock_tag !== "low" && r.stock_tag !== "out") return false;
      if (stockFilter === "out" && r.stock_tag !== "out") return false;
      if (rxFilter === "rx" && !r.is_controlled) return false;
      if (rxFilter === "otc" && r.is_controlled) return false;
      if (!q) return true;
      return (
        r.drug_name.toLowerCase().includes(q) ||
        r.drug_code.toLowerCase().includes(q) ||
        (r.drug_brand?.toLowerCase().includes(q) ?? false)
      );
    });

    const dir = sort.dir === "asc" ? 1 : -1;
    out.sort((a, b) => {
      const av = a[sort.key];
      const bv = b[sort.key];
      if (typeof av === "number" && typeof bv === "number") return (av - bv) * dir;
      return String(av ?? "").localeCompare(String(bv ?? ""), undefined, {
        sensitivity: "base",
      }) * dir;
    });
    return out;
  }, [allRows, query, stockFilter, rxFilter, sort]);

  // Reset active row when filters change
  useEffect(() => {
    setActiveIdx(0);
  }, [query, stockFilter, rxFilter]);

  const qtyFor = useCallback((code: string) => qtyMap[code] ?? 1, [qtyMap]);
  const setQty = useCallback((code: string, n: number) => {
    setQtyMap((m) => ({ ...m, [code]: Math.max(1, Math.min(99, Number.isFinite(n) ? n : 1)) }));
  }, []);

  const handleAdd = useCallback(
    (row: (typeof filtered)[number], qtyOverride?: number) => {
      if (row.stock_tag === "out") return;
      const want = qtyOverride ?? qtyFor(row.drug_code);
      addItem({
        drug_code: row.drug_code,
        drug_name: row.drug_name,
        batch_number: null,
        expiry_date: null,
        quantity: want,
        unit_price: row.unit_price,
        discount: 0,
        line_total: want * row.unit_price,
        is_controlled: row.is_controlled,
      });
      toast.success(`+${want} · ${row.drug_name}`);
      setQtyMap((m) => ({ ...m, [row.drug_code]: 1 }));
    },
    [addItem, qtyFor, toast],
  );

  const toggleSort = useCallback((key: SortKey) => {
    setSort((s) => (s.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: "asc" }));
  }, []);

  const handleStocktaking = useCallback(() => {
    setStocktakingOpen(true);
  }, []);

  // ---- Keyboard nav (scoped to this page) ----
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName ?? "";
      const isInput = tag === "INPUT" || tag === "TEXTAREA";

      if (e.key === "/" && !isInput) {
        e.preventDefault();
        searchRef.current?.focus();
        return;
      }
      if (e.key === "F6") {
        e.preventDefault();
        handleStocktaking();
        return;
      }
      if (e.key === "Escape" && isInput && target === searchRef.current) {
        searchRef.current?.blur();
        return;
      }
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIdx((i) => Math.min(Math.max(filtered.length - 1, 0), i + 1));
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIdx((i) => Math.max(0, i - 1));
        return;
      }
      if (e.key === "Enter" && isInput && filtered[activeIdx]) {
        e.preventDefault();
        handleAdd(filtered[activeIdx]);
        return;
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [filtered, activeIdx, handleAdd, handleStocktaking]);

  // Summary stats
  const totalSkus = allRows.length;
  const totalUnits = allRows.reduce((s, r) => s + (r.stock_available || 0), 0);
  const stockValue = allRows.reduce((s, r) => s + (r.stock_available || 0) * r.unit_price, 0);
  const lowCount = allRows.filter((r) => r.stock_tag === "low").length;
  const outCount = allRows.filter((r) => r.stock_tag === "out").length;

  const activeRow = filtered[activeIdx] ?? null;

  return (
    <div
      className={cn(
        "pos-root flex min-h-screen flex-col overflow-hidden text-text-primary",
      )}
      data-testid="pos-drugs-page"
    >
      <header className="flex h-14 items-center justify-between border-b border-[var(--pos-line)] bg-[var(--pos-card)] px-4">
        <div className="flex items-center gap-3">
          <OfflineBadge />
          <span
            className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-cyan-300"
            aria-hidden="true"
          >
            ● Drugs
          </span>
          <span className="font-[family-name:var(--font-fraunces)] text-sm italic text-text-primary">
            Catalog &amp; inventory
          </span>
        </div>
        <div className="flex items-center gap-3">
          {terminal && (
            <div className="flex items-center gap-1.5 font-mono text-xs text-text-secondary">
              <Clock className="h-3.5 w-3.5" />
              <span>{terminal.terminal_name}</span>
            </div>
          )}
          <button
            type="button"
            onClick={() => router.push("/terminal")}
            data-testid="drugs-close-button"
            className={cn(
              "flex items-center gap-1.5 rounded-lg border border-[var(--pos-line)] px-3 py-1.5",
              "text-xs font-medium text-text-secondary hover:bg-[var(--pos-card)]",
            )}
          >
            <X className="h-3.5 w-3.5" />
            Close
          </button>
        </div>
      </header>

      <main
        className={cn(
          "grid flex-1 gap-3.5 overflow-hidden p-3.5",
          "grid-cols-[minmax(0,1fr)_320px]",
        )}
      >
        <section className="flex min-h-0 min-w-0 flex-col gap-3">
          <DrugsSearchBar
            ref={searchRef}
            query={query}
            onQueryChange={setQuery}
            stockFilter={stockFilter}
            onStockFilterChange={setStockFilter}
            rxFilter={rxFilter}
            onRxFilterChange={setRxFilter}
            resultCount={filtered.length}
            totalCount={totalSkus}
            onOpenStocktaking={handleStocktaking}
          />
          <DrugsTable
            rows={filtered}
            activeIdx={activeIdx}
            onActivateIdx={setActiveIdx}
            qtyFor={qtyFor}
            onQtyChange={setQty}
            onAdd={handleAdd}
            sort={sort}
            onSortToggle={toggleSort}
          />
        </section>

        <aside className="flex min-h-0 flex-col gap-3 overflow-y-auto">
          <InventorySummary
            totalSkus={totalSkus}
            totalUnits={totalUnits}
            stockValue={stockValue}
            lowCount={lowCount}
            outCount={outCount}
          />
          <FocusedDrug row={activeRow} qty={activeRow ? qtyFor(activeRow.drug_code) : 1} onAdd={handleAdd} />
          <CartGoTo itemCount={itemCount} grandTotal={grandTotal} />
        </aside>
      </main>
      <StocktakingModal
        open={stocktakingOpen}
        onClose={() => setStocktakingOpen(false)}
        rows={allRows}
        branchName={posBranding.branchName}
        branchAddress={posBranding.branchAddress}
        crNumber={posBranding.crNumber}
      />
    </div>
  );
}
