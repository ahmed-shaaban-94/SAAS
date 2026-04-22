"use client";

/**
 * ShiftOpenModal — blocks the terminal until a shift is opened with an
 * opening cash float (issue #632, D5).
 *
 * Replaces the previous `/shift` redirect: the modal appears inline
 * whenever there is no active terminal session. On success it stores
 * the new session in localStorage and calls `onOpened`.
 */

import { useEffect, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from "react";
import { Banknote, Loader2 } from "lucide-react";
import { openTerminal } from "@/hooks/use-pos-terminal";
import { cn } from "@/lib/utils";
import type { TerminalSessionResponse } from "@/types/pos";

interface ShiftOpenModalProps {
  terminalName?: string;
  siteCode?: string;
  onOpened: (session: TerminalSessionResponse) => void;
}

export function ShiftOpenModal({
  terminalName = "Terminal-1",
  siteCode = "SITE01",
  onOpened,
}: ShiftOpenModalProps) {
  const [cash, setCash] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  async function handleOpen() {
    const amount = parseFloat(cash);
    if (isNaN(amount) || amount < 0) {
      setError("أدخل مبلغ صحيحاً");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const session = await openTerminal({
        site_code: siteCode,
        terminal_name: terminalName,
        opening_cash: amount,
      });
      localStorage.setItem("pos:active_terminal", JSON.stringify(session));
      onOpened(session);
    } catch (e) {
      setError(e instanceof Error ? e.message : "فشل فتح الوردية — حاول مجدداً");
    } finally {
      setIsLoading(false);
    }
  }

  function handleKeyDown(e: ReactKeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      void handleOpen();
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/90 backdrop-blur-md">
      <div
        className={cn(
          "w-full max-w-xs rounded-2xl border border-[var(--pos-line)] bg-[var(--pos-card)] p-6 shadow-2xl",
        )}
        data-testid="shift-open-modal"
      >
        {/* Icon + heading */}
        <div className="mb-5 flex flex-col items-center gap-2">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-cyan-400/10">
            <Banknote className="h-7 w-7 text-cyan-300" />
          </div>
          <h2 className="pos-display text-[17px] text-text-primary">فتح الوردية</h2>
          <p className="text-center font-mono text-[11px] text-text-secondary">
            {terminalName} · {siteCode}
          </p>
        </div>

        {/* Cash input */}
        <label className="mb-1 block font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-text-secondary">
          رصيد الصندوق الافتتاحي
        </label>
        <div className="relative mb-4">
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 font-mono text-[11px] font-semibold uppercase text-cyan-300">
            EGP
          </span>
          <input
            ref={inputRef}
            type="number"
            min="0"
            step="0.01"
            value={cash}
            onChange={(e) => {
              setError(null);
              setCash(e.target.value);
            }}
            onKeyDown={handleKeyDown}
            className={cn(
              "w-full rounded-xl border border-[var(--pos-line)] bg-[var(--pos-bg)] py-3 ps-12 pe-4",
              "font-mono tabular-nums text-[22px] font-semibold text-text-primary",
              "focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400/50",
              error && "border-red-500/70",
            )}
            placeholder="0.00"
            disabled={isLoading}
          />
        </div>

        {error && (
          <p className="mb-3 text-center font-mono text-[11px] text-red-400">{error}</p>
        )}

        <button
          type="button"
          onClick={() => void handleOpen()}
          disabled={isLoading}
          className={cn(
            "flex w-full items-center justify-center gap-2 rounded-xl py-3",
            "bg-cyan-500 font-mono text-[13px] font-bold uppercase tracking-[0.15em] text-black",
            "transition hover:bg-cyan-400 active:scale-[0.98]",
            "disabled:cursor-not-allowed disabled:opacity-50",
          )}
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            "فتح الوردية ↵"
          )}
        </button>
      </div>
    </div>
  );
}
