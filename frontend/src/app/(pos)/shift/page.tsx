"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Monitor, DollarSign, Loader2 } from "lucide-react";
import { ShiftSummary } from "@/components/pos/ShiftSummary";
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

  // Restore active terminal from storage
  const [terminal, setTerminal] = useState<TerminalSessionResponse | null>(() => {
    if (typeof window === "undefined") return null;
    const stored = localStorage.getItem("pos:active_terminal");
    return stored ? (JSON.parse(stored) as TerminalSessionResponse) : null;
  });

  const [view, setView] = useState<ShiftView>(terminal ? "active" : "open");
  const [shiftResult, setShiftResult] = useState<TerminalSessionResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Open shift form
  const [terminalName, setTerminalName] = useState("Terminal-1");
  const [siteCode, setSiteCode] = useState("SITE01");
  const [openingCash, setOpeningCash] = useState("");

  // Close shift form
  const [closingCash, setClosingCash] = useState("");

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

  async function handleCloseTerminal() {
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
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex h-14 items-center border-b border-border bg-surface px-4">
        <div className="flex items-center gap-2">
          <Monitor className="h-4 w-4 text-text-secondary" />
          <span className="text-sm font-semibold text-text-primary">
            {view === "open" ? "Open Terminal" : view === "active" ? "Active Terminal" : view === "close" ? "Close Shift" : "Shift Summary"}
          </span>
        </div>
      </header>

      <main className="flex flex-1 flex-col items-center justify-center p-6">
        <div className="w-full max-w-sm space-y-4">
          {/* Open Terminal */}
          {view === "open" && (
            <>
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
                {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <DollarSign className="h-4 w-4" />}
                Open Terminal
              </button>
            </>
          )}

          {/* Active terminal */}
          {view === "active" && terminal && (
            <>
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
            </>
          )}

          {/* Close shift */}
          {view === "close" && terminal && (
            <>
              <p className="text-sm text-text-secondary">Count the cash in the drawer and enter the amount:</p>
              <CashInput label="Closing Cash Count" value={closingCash} onChange={setClosingCash} />
              {error && <p className="text-xs text-destructive">{error}</p>}
              <button
                type="button"
                onClick={handleCloseTerminal}
                disabled={isLoading}
                className={cn(
                  "flex w-full items-center justify-center gap-2 rounded-xl py-3",
                  "bg-destructive/80 text-sm font-semibold text-white",
                  "hover:bg-destructive disabled:pointer-events-none disabled:opacity-40",
                )}
              >
                {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Close Shift
              </button>
              <button
                type="button"
                onClick={() => setView("active")}
                className="w-full rounded-xl border border-border py-3 text-sm font-medium text-text-secondary hover:bg-surface-raised"
              >
                Cancel
              </button>
            </>
          )}

          {/* Shift summary after close */}
          {view === "closed" && shiftResult && (
            <>
              <ShiftSummary shiftData={shiftResult} />
              <button
                type="button"
                onClick={() => setView("open")}
                className="w-full rounded-xl bg-accent py-3 text-sm font-semibold text-accent-foreground hover:bg-accent/90"
              >
                Open New Terminal
              </button>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
