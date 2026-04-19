"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  RefreshCw,
  RotateCcw,
  XCircle,
} from "lucide-react";
import { ReconcileModal } from "@/components/pos/ReconcileModal";
import { usePosSyncIssues } from "@/hooks/use-pos-sync-issues";
import { hasElectron } from "@/lib/pos/ipc";
import type { ReconcileKind } from "@/lib/pos/offline-db";
import type { QueueRow } from "@/lib/pos/ipc";
import { cn } from "@/lib/utils";

interface ModalTarget {
  row: QueueRow;
  kind: ReconcileKind;
}

function formatElapsed(isoDate: string): string {
  const diffMs = Date.now() - new Date(isoDate).getTime();
  const mins = Math.floor(diffMs / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function PosSyncIssuesPage() {
  const router = useRouter();
  const { items, isLoading, isError, mutate } = usePosSyncIssues();
  const [target, setTarget] = useState<ModalTarget | null>(null);

  const electronAvailable = useMemo(() => hasElectron(), []);

  function handleSuccess() {
    setTarget(null);
    void mutate();
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex h-14 items-center justify-between border-b border-border bg-surface px-4">
        <button
          type="button"
          onClick={() => router.push("/terminal")}
          className="flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>
        <span className="text-sm font-semibold text-text-primary">Sync Issues</span>
        <button
          type="button"
          onClick={() => void mutate()}
          aria-label="Refresh"
          className="rounded-lg p-1.5 text-text-secondary hover:bg-surface-raised"
        >
          <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
        </button>
      </header>

      <main className="flex-1 overflow-y-auto p-4">
        {!electronAvailable && (
          <div
            className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-center text-sm text-amber-400"
            role="status"
            aria-live="polite"
          >
            Sync Issues is only available in the desktop app.
          </div>
        )}

        {electronAvailable && isError && (
          <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-center text-sm text-destructive">
            Failed to load sync issues
          </div>
        )}

        {electronAvailable && isLoading && items.length === 0 && (
          <div className="space-y-2" data-testid="sync-issues-skeleton">
            {Array.from({ length: 4 }, (_, i) => (
              <div key={i} className="h-24 animate-pulse rounded-xl bg-surface" />
            ))}
          </div>
        )}

        {electronAvailable && !isLoading && items.length === 0 && (
          <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
            <CheckCircle2 className="h-12 w-12 text-green-400" />
            <p className="text-sm font-medium text-text-primary">
              No unresolved sync issues
            </p>
            <p className="text-xs text-text-secondary">Shift can be closed.</p>
          </div>
        )}

        {electronAvailable && items.length > 0 && (
          <div className="space-y-2">
            {items.map((row) => (
              <div
                key={row.local_id}
                className="rounded-xl border border-destructive/30 bg-surface p-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="truncate font-mono text-xs text-text-primary">
                        {row.endpoint}
                      </span>
                      <span className="rounded-full bg-destructive/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-destructive">
                        rejected
                      </span>
                    </div>
                    <p className="mt-0.5 text-xs text-text-secondary">
                      {formatElapsed(row.created_at)} · retries: {row.retry_count}
                    </p>
                  </div>
                </div>

                {row.last_error && (
                  <div className="mt-2 flex items-start gap-1.5 rounded-lg bg-destructive/10 p-2">
                    <AlertTriangle className="mt-0.5 h-3 w-3 flex-shrink-0 text-destructive" />
                    <p className="break-words text-xs text-destructive">{row.last_error}</p>
                  </div>
                )}

                <div className="mt-3 flex flex-col gap-2 border-t border-border/50 pt-2 sm:flex-row">
                  <button
                    type="button"
                    onClick={() => setTarget({ row, kind: "retry_override" })}
                    className={cn(
                      "flex flex-1 items-center justify-center gap-1.5 rounded-lg py-1.5",
                      "bg-accent text-xs font-medium text-white",
                      "hover:bg-accent/90 transition-colors",
                    )}
                  >
                    <RefreshCw className="h-3 w-3" />
                    Retry with override
                  </button>
                  <button
                    type="button"
                    onClick={() => setTarget({ row, kind: "record_loss" })}
                    className={cn(
                      "flex flex-1 items-center justify-center gap-1.5 rounded-lg py-1.5",
                      "border border-destructive/30 bg-destructive/10 text-xs font-medium text-destructive",
                      "hover:bg-destructive/20 transition-colors",
                    )}
                  >
                    <XCircle className="h-3 w-3" />
                    Record as loss
                  </button>
                  <button
                    type="button"
                    onClick={() => setTarget({ row, kind: "corrective_void" })}
                    className={cn(
                      "flex flex-1 items-center justify-center gap-1.5 rounded-lg py-1.5",
                      "border border-amber-500/30 bg-amber-500/10 text-xs font-medium text-amber-400",
                      "hover:bg-amber-500/20 transition-colors",
                    )}
                  >
                    <RotateCcw className="h-3 w-3" />
                    Corrective void
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {target && (
        <ReconcileModal
          row={target.row}
          kind={target.kind}
          onSuccess={handleSuccess}
          onCancel={() => setTarget(null)}
        />
      )}
    </div>
  );
}
