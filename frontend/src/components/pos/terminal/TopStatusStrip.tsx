"use client";

import { useEffect, useState } from "react";
import { Star, Trophy, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useOfflineState } from "@/hooks/use-offline-state";
import type { ActiveShift } from "@/hooks/use-active-shift";

// ── helpers ───────────────────────────────────────────────────────────────────

function fmtEgp(n: number): string {
  return n.toLocaleString("ar-EG", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function fmtTime(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString("ar-EG", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

const STRIP_MONO =
  "font-mono text-[10px] uppercase tracking-[0.14em]";

// ── SyncPill ─────────────────────────────────────────────────────────────────

function SyncPill() {
  const { isOnline, unresolved, lastSyncAt } = useOfflineState();

  if (!isOnline) {
    return (
      <span
        data-testid="sync-pill-offline"
        role="status"
        className={cn(
          STRIP_MONO,
          "flex items-center gap-1.5 rounded-full bg-destructive/20 px-3 py-1 text-destructive",
        )}
      >
        ✕ OFFLINE{unresolved > 0 ? ` · ${unresolved}` : ""}
      </span>
    );
  }

  if (unresolved > 0) {
    return (
      <span
        data-testid="sync-pill-pending"
        role="status"
        className={cn(
          STRIP_MONO,
          "flex items-center gap-1.5 rounded-full bg-amber-500/20 px-3 py-1 text-amber-400",
        )}
      >
        ⟳ {unresolved} pending
      </span>
    );
  }

  return (
    <span
      data-testid="sync-pill-synced"
      role="status"
      className={cn(
        STRIP_MONO,
        "flex items-center gap-1.5 rounded-full bg-green-500/15 px-3 py-1 text-green-400",
      )}
    >
      ● SYNCED{lastSyncAt ? ` · ${fmtTime(lastSyncAt)}` : ""}
    </span>
  );
}

// ── CommissionPill ────────────────────────────────────────────────────────────

interface CommissionPillProps {
  earned: number;
}

function CommissionPill({ earned }: CommissionPillProps) {
  return (
    <span
      data-testid="commission-pill"
      className={cn(
        STRIP_MONO,
        "flex items-center gap-1 rounded-full bg-yellow-500/15 px-3 py-1 text-yellow-300",
      )}
    >
      <Star
        className={cn(
          "h-3 w-3 fill-yellow-400 text-yellow-400",
          // pulsing star disabled when prefers-reduced-motion
          "motion-safe:animate-pulse",
        )}
        aria-hidden="true"
      />
      {fmtEgp(earned)} جنيه
    </span>
  );
}

// ── TargetBar ────────────────────────────────────────────────────────────────

interface TargetBarProps {
  current: number;
  target: number;
  txnCount: number;
}

function TargetBar({ current, target, txnCount }: TargetBarProps) {
  const pct = target > 0 ? Math.min(100, Math.round((current / target) * 100)) : 0;

  return (
    <div data-testid="target-bar" className="flex items-center gap-2">
      <Trophy className="h-3 w-3 shrink-0 text-yellow-400" aria-hidden="true" />
      <div className="flex w-24 flex-col gap-0.5">
        <div className="h-[4px] w-full overflow-hidden rounded-full bg-white/10">
          <div
            role="progressbar"
            aria-valuenow={pct}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`Daily target ${pct}%`}
            style={{
              width: `${pct}%`,
              background: "linear-gradient(to right, #facc15, #f59e0b)",
            }}
            className="h-full rounded-full transition-all duration-500"
          />
        </div>
        <span className={cn(STRIP_MONO, "text-yellow-300/70")}>
          {pct}% · {txnCount} txn
        </span>
      </div>
    </div>
  );
}

// ── DigitalClock ─────────────────────────────────────────────────────────────

function DigitalClock() {
  const [time, setTime] = useState(() =>
    new Date().toLocaleTimeString("ar-EG", { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
  );

  useEffect(() => {
    const id = setInterval(() => {
      setTime(new Date().toLocaleTimeString("ar-EG", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }));
    }, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <span
      data-testid="digital-clock"
      className={cn(STRIP_MONO, "tabular-nums text-text-secondary")}
      aria-label="Current time"
    >
      {time}
    </span>
  );
}

// ── TopStatusStrip ────────────────────────────────────────────────────────────

interface TopStatusStripProps {
  shift: ActiveShift | null;
  terminalName?: string;
  onClose: () => void;
}

export function TopStatusStrip({ shift, terminalName, onClose }: TopStatusStripProps) {
  return (
    <header
      data-testid="top-status-strip"
      data-no-print="true"
      className="flex h-14 items-center justify-between border-b border-[var(--pos-line)] bg-[var(--pos-card)] px-4"
    >
      {/* Left: sync pill */}
      <div className="flex items-center gap-3">
        <SyncPill />
        {terminalName && (
          <span className={cn(STRIP_MONO, "text-text-secondary/70")}>{terminalName}</span>
        )}
      </div>

      {/* Center: digital clock */}
      <DigitalClock />

      {/* Right: commission + target + close */}
      <div className="flex items-center gap-3">
        {shift && (
          <>
            <CommissionPill earned={shift.commission_earned_egp} />
            {shift.daily_sales_target_egp !== null && shift.daily_sales_target_egp > 0 && (
              <TargetBar
                current={shift.sales_so_far_egp}
                target={shift.daily_sales_target_egp}
                txnCount={shift.transactions_so_far}
              />
            )}
          </>
        )}
        <button
          type="button"
          onClick={onClose}
          data-testid="close-terminal-btn"
          aria-label="Close terminal"
          className={cn(
            "flex items-center gap-1.5 rounded-lg border border-[var(--pos-line)] px-3 py-1.5",
            "font-mono text-[10px] uppercase tracking-[0.14em] text-text-secondary",
            "hover:bg-surface-raised",
          )}
        >
          <X className="h-3.5 w-3.5" />
          Close
        </button>
      </div>
    </header>
  );
}
