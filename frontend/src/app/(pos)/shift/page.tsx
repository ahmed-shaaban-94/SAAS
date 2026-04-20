"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, DollarSign, Loader2, Monitor } from "lucide-react";
import { ShiftSummary } from "@/components/pos/ShiftSummary";
import { ReconcileGrid } from "@/components/pos/shift/ReconcileGrid";
import { ThermalShiftReceipt } from "@/components/pos/shift/ThermalShiftReceipt";
import { openTerminal, closeTerminal } from "@/hooks/use-pos-terminal";
import { cn } from "@/lib/utils";
import type { TerminalSessionResponse } from "@/types/pos";

type ShiftView = "open" | "active" | "close" | "closed";

function CashInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-text-secondary">{label}</label>
      <div className="relative">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-text-secondary">
          EGP
        </span>
        <input
          type="number"
          min="0"
          step="0.01"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={cn(
            "w-full rounded-xl border border-border bg-surface py-3 pl-12 pr-4",
            "text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent",
          )}
          placeholder="0.00"
        />
      </div>
    </div>
  );
}

export default function ShiftPage() {
  const router = useRouter();

  const [terminal, setTerminal] = useState<TerminalSessionResponse | null>(() => {
    if (typeof window === "undefined") return null;
    const stored = localStorage.getItem("pos:active_terminal");
    return stored ? (JSON.parse(stored) as TerminalSessionResponse) : null;
  });

  const [view, setView] = useState<ShiftView>(terminal ? "active" : "open");
  const [shiftResult, setShiftResult] = useState<TerminalSessionResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [terminalName, setTerminalName] = useState("Terminal-1");
  const [siteCode, setSiteCode] = useState("SITE01");
  const [openingCash, setOpeningCash] = useState("");
  const [closingCash, setClosingCash] = useState("");

  // Cash sales isn't returned by the close endpoint yet — treated as 0 by
  // default so variance = counted - opening until the server exposes it.
  const cashSales = 0;

  async function handleOpenTerminal() {
    setIsLoading(true);
    setError(null);
    try {
      const t = await openTerminal({
        site_code: siteCode,
        terminal_name: terminalName,
        opening_cash: parseFloat(openingCash) || 0,
      });
      localStorage.setItem("pos:active_terminal", JSON.stringify(t));
      setTerminal(t);
      setView("active");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to open terminal");
    } finally {
      setIsLoading(false);
    }
  }

  const handleCloseTerminal = useCallback(async () => {
    if (!terminal) return;
    setIsLoading(true);
    setError(null);
    try {
      const summary = await closeTerminal(terminal.id, {
        closing_cash: parseFloat(closingCash) || 0,
      });
      localStorage.removeItem("pos:active_terminal");
      setTerminal(null);
      setShiftResult(summary);
      setView("closed");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to close terminal");
    } finally {
      setIsLoading(false);
    }
  }, [terminal, closingCash]);

  const handlePrint = useCallback(() => {
    if (typeof window !== "undefined") window.print();
  }, []);

  useEffect(() => {
    if (view !== "close") return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "F4") {
        e.preventDefault();
        handlePrint();
      } else if (e.key === "Enter") {
        const tag = (e.target as HTMLElement | null)?.tagName ?? "";
        if (tag === "INPUT" || tag === "TEXTAREA") {
          e.preventDefault();
          void handleCloseTerminal();
        }
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [view, handlePrint, handleCloseTerminal]);

  return (
    <div className="flex min-h-screen flex-col" data-testid="pos-shift-page">
      <header
        className="flex h-14 items-center justify-between border-b border-border bg-surface px-4 print:hidden"
        data-print-hide
      >
        <button
          type="button"
          onClick={() => router.push("/terminal")}
          className="flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>
        <div className="flex items-center gap-2">
          <Monitor className="h-4 w-4 text-text-secondary" />
          <span className="text-sm font-semibold text-text-primary">
            {view === "open"
              ? "Open Terminal"
              : view === "active"
                ? "Active Terminal"
                : view === "close"
                  ? "Close Shift"
                  : "Shift Summary"}
          </span>
        </div>
        <div className="w-16" />
      </header>

      <main className="flex flex-1 flex-col p-4 md:p-6">
        {view === "open" && (
          <div className="mx-auto w-full max-w-sm space-y-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">
                Terminal Name
              </label>
              <input
                type="text"
                value={terminalName}
                onChange={(e) => setTerminalName(e.target.value)}
                className="w-full rounded-xl border border-border bg-surface px-4 py-3 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">
                Site Code
              </label>
              <input
                type="text"
                value={siteCode}
                onChange={(e) => setSiteCode(e.target.value)}
                className="w-full rounded-xl border border-border bg-surface px-4 py-3 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </div>
            <CashInput label="Opening Cash" value={openingCash} onChange={setOpeningCash} />
            {error && <p className="text-xs text-destructive">{error}</p>}
            <button
              type="button"
              onClick={handleOpenTerminal}
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
                <DollarSign className="h-4 w-4" />
              )}
              Open Terminal
            </button>
          </div>
        )}

        {view === "active" && terminal && (
          <div className="mx-auto w-full max-w-sm space-y-4">
            <div className="rounded-xl border border-accent/20 bg-accent/5 p-4 text-center">
              <p className="text-xs text-text-secondary">Active Terminal</p>
              <p className="mt-1 text-lg font-bold text-text-primary">{terminal.terminal_name}</p>
              <p className="text-xs text-text-secondary">Site: {terminal.site_code}</p>
            </div>
            <button
              type="button"
              onClick={() => router.push("/terminal")}
              className="w-full rounded-xl bg-accent py-3 text-sm font-semibold text-accent-foreground hover:bg-accent/90"
            >
              Go to POS Terminal
            </button>
            <button
              type="button"
              onClick={() => setView("close")}
              className="w-full rounded-xl border border-border py-3 text-sm font-medium text-text-secondary hover:bg-surface-raised"
            >
              Close Shift
            </button>
          </div>
        )}

        {view === "close" && terminal && (
          <div className="mx-auto grid w-full max-w-5xl gap-6 md:grid-cols-[1fr_360px]">
            <section
              className="flex flex-col gap-4 print:hidden"
              data-testid="shift-close-reconcile"
            >
              <div>
                <div
                  className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-accent"
                  aria-hidden="true"
                >
                  ● Shift close
                </div>
                <h1 className="mt-1.5 font-[family-name:var(--font-fraunces)] text-2xl italic text-text-primary">
                  Reconcile cash, print the report
                </h1>
                <p className="mt-1 text-xs text-text-secondary">
                  Count the drawer, resolve any variance, then finalize.
                </p>
              </div>

              <ReconcileGrid
                opening={terminal.opening_cash ?? 0}
                cashSales={cashSales}
                counted={closingCash}
                onCountedChange={setClosingCash}
                onFinalize={handleCloseTerminal}
                onPrint={handlePrint}
                isLoading={isLoading}
                canFinalize={closingCash.length > 0}
              />

              {error && (
                <p className="text-xs text-destructive" role="alert">
                  {error}
                </p>
              )}

              <button
                type="button"
                onClick={() => setView("active")}
                className="self-start rounded-xl border border-border px-4 py-2 text-xs font-medium text-text-secondary hover:bg-surface-raised"
              >
                Cancel
              </button>
            </section>

            <section data-testid="shift-receipt-preview">
              <div className="mb-2 font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-text-secondary print:hidden">
                Receipt preview · 80mm
              </div>
              <ThermalShiftReceipt
                branchName={`Site ${terminal.site_code}`}
                taxNo="345-678-901"
                terminalName={terminal.terminal_name}
                cashierName={terminal.staff_id}
                openedAt={terminal.opened_at}
                opening={terminal.opening_cash ?? 0}
                cashSales={cashSales}
                counted={parseFloat(closingCash || "0")}
              />
              <p className="mt-2 text-center font-mono text-[10px] uppercase tracking-[0.12em] text-text-secondary print:hidden">
                Parity with 80mm thermal output
              </p>
            </section>
          </div>
        )}

        {view === "closed" && shiftResult && (
          <div className="mx-auto w-full max-w-sm space-y-4">
            <ShiftSummary shiftData={shiftResult} />
            <button
              type="button"
              onClick={() => setView("open")}
              className="w-full rounded-xl bg-accent py-3 text-sm font-semibold text-accent-foreground hover:bg-accent/90"
            >
              Open New Terminal
            </button>
          </div>
        )}
      </main>

      <style
        dangerouslySetInnerHTML={{
          __html: `
            @media print {
              @page { size: 80mm auto; margin: 0; }
              body { background: #fff !important; }
              [data-print-hide], .print\\:hidden { display: none !important; }
              [data-testid="shift-receipt-preview"] { width: 80mm !important; margin: 0 auto !important; }
            }
          `,
        }}
      />
    </div>
  );
}
