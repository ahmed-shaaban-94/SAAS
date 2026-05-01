import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@shared/lib/utils";
import type { TerminalSessionResponse } from "@pos/types/pos";

interface ShiftSummaryProps {
  shiftData: TerminalSessionResponse;
}

function fmt(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  return n.toLocaleString("ar-EG", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function VarianceIndicator({ variance }: { variance: number | null }) {
  if (variance === null) return <Minus className="h-4 w-4 text-text-secondary" />;
  if (variance > 0) return <TrendingUp className="h-4 w-4 text-green-400" />;
  if (variance < 0) return <TrendingDown className="h-4 w-4 text-destructive" />;
  return <Minus className="h-4 w-4 text-text-secondary" />;
}

export function ShiftSummary({ shiftData }: ShiftSummaryProps) {
  const variance =
    shiftData.closing_cash !== null && shiftData.opening_cash !== null
      ? shiftData.closing_cash - shiftData.opening_cash
      : null;

  const shiftDate = new Date(shiftData.opened_at).toLocaleDateString();

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="rounded-xl border border-border bg-surface p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-text-secondary">Shift Date</p>
            <p className="text-sm font-semibold text-text-primary">{shiftDate}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-text-secondary">Cashier</p>
            <p className="text-sm font-semibold text-text-primary">{shiftData.staff_id}</p>
          </div>
        </div>
        <div className="mt-2 flex justify-between text-xs text-text-secondary">
          <span>Opened: {new Date(shiftData.opened_at).toLocaleTimeString()}</span>
          {shiftData.closed_at && (
            <span>Closed: {new Date(shiftData.closed_at).toLocaleTimeString()}</span>
          )}
        </div>
      </div>

      {/* Cash Variance */}
      <div
        className={cn(
          "rounded-xl border bg-surface p-3",
          variance === null
            ? "border-border"
            : variance > 0
              ? "border-green-500/30"
              : variance < 0
                ? "border-destructive/30"
                : "border-border",
        )}
      >
        <div className="flex items-center justify-between">
          <p className="text-xs text-text-secondary">Cash Variance</p>
          <VarianceIndicator variance={variance} />
        </div>
        <p
          className={cn(
            "mt-1 text-base font-bold tabular-nums",
            variance === null
              ? "text-text-primary"
              : variance > 0
                ? "text-green-400"
                : variance < 0
                  ? "text-destructive"
                  : "text-text-primary",
          )}
        >
          {variance !== null ? `EGP ${fmt(Math.abs(variance))}` : "—"}
        </p>
      </div>

      {/* Cash reconciliation */}
      <div className="rounded-xl border border-border bg-surface p-4 space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
          Cash Reconciliation
        </p>
        <div className="flex justify-between text-sm">
          <span className="text-text-secondary">Opening Cash</span>
          <span className="tabular-nums text-text-primary">EGP {fmt(shiftData.opening_cash)}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-text-secondary">Closing Count</span>
          <span className="tabular-nums text-text-primary">EGP {fmt(shiftData.closing_cash)}</span>
        </div>
      </div>
    </div>
  );
}
