"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, CheckCircle2, RefreshCw } from "lucide-react";
import { ReconcileModal } from "@/components/pos/ReconcileModal";
import { IssueCard, type IssueAction } from "@/components/pos/sync/IssueCard";
import { LegendBar } from "@/components/pos/sync/LegendBar";
import { usePosSyncIssues } from "@/hooks/use-pos-sync-issues";
import { hasElectron } from "@/lib/pos/ipc";
import type { ReconcileKind } from "@/lib/pos/offline-db";
import type { QueueRow } from "@/lib/pos/ipc";
import { cn } from "@/lib/utils";

interface ModalTarget {
  row: QueueRow;
  kind: ReconcileKind;
}

export default function PosSyncIssuesPage() {
  const router = useRouter();
  const { items, isLoading, isError, mutate } = usePosSyncIssues();
  const [target, setTarget] = useState<ModalTarget | null>(null);
  const [activeIdx, setActiveIdx] = useState(0);

  const electronAvailable = useMemo(() => hasElectron(), []);

  useEffect(() => {
    if (activeIdx >= items.length) setActiveIdx(0);
  }, [items.length, activeIdx]);

  const handleAction = useCallback(
    (row: QueueRow, kind: IssueAction) => setTarget({ row, kind }),
    [],
  );

  const handleSuccess = useCallback(() => {
    setTarget(null);
    void mutate();
  }, [mutate]);

  // Keyboard nav: ↑↓ to move selection, O/L/R to open action modal
  useEffect(() => {
    if (!electronAvailable) return;
    function onKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement | null)?.tagName ?? "";
      const isInput = tag === "INPUT" || tag === "TEXTAREA";
      if (isInput) return;
      if (items.length === 0) return;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIdx((i) => Math.min(items.length - 1, i + 1));
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIdx((i) => Math.max(0, i - 1));
        return;
      }
      const row = items[activeIdx];
      if (!row) return;
      if (e.key === "o" || e.key === "O") {
        e.preventDefault();
        setTarget({ row, kind: "retry_override" });
        return;
      }
      if (e.key === "l" || e.key === "L") {
        e.preventDefault();
        setTarget({ row, kind: "record_loss" });
        return;
      }
      if (e.key === "r" || e.key === "R") {
        e.preventDefault();
        setTarget({ row, kind: "corrective_void" });
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [items, activeIdx, electronAvailable]);

  return (
    <div className="flex min-h-screen flex-col" data-testid="pos-sync-issues-page">
      <header className="flex h-14 items-center justify-between border-b border-border bg-surface px-4">
        <button
          type="button"
          onClick={() => router.push("/terminal")}
          className="flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>
        <div className="flex flex-col items-center">
          <span
            className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-accent"
            aria-hidden="true"
          >
            ● Sync Issues
          </span>
          <span className="font-[family-name:var(--font-fraunces)] text-xl italic text-text-primary">
            Reconcile the queue
          </span>
        </div>
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
        <div className="mx-auto flex w-full max-w-4xl flex-col gap-3">
          {!electronAvailable && (
            <div
              className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-center text-sm text-amber-400"
              role="status"
              aria-live="polite"
            >
              Sync Issues is only available in the desktop app.
            </div>
          )}

          {electronAvailable && <LegendBar />}

          {electronAvailable && isError && (
            <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-center text-sm text-destructive">
              Failed to load sync issues
            </div>
          )}

          {electronAvailable && isLoading && items.length === 0 && (
            <div className="space-y-2" data-testid="sync-issues-skeleton">
              {Array.from({ length: 4 }, (_, i) => (
                <div key={i} className="h-20 animate-pulse rounded-xl bg-surface" />
              ))}
            </div>
          )}

          {electronAvailable && !isLoading && items.length === 0 && (
            <div
              className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-green-500/40 bg-green-500/5 py-16 text-center"
              data-testid="sync-issues-empty"
            >
              <CheckCircle2 className="h-10 w-10 text-green-400" />
              <p className="font-[family-name:var(--font-fraunces)] text-lg italic text-text-primary">
                All transactions synced
              </p>
              <p className="text-xs text-text-secondary">Shift can be closed.</p>
            </div>
          )}

          {electronAvailable && items.length > 0 && (
            <div className="flex flex-col gap-2" data-testid="sync-issues-list">
              {items.map((row, idx) => (
                <IssueCard
                  key={row.local_id}
                  row={row}
                  isActive={idx === activeIdx}
                  onSelect={() => setActiveIdx(idx)}
                  onAction={(kind) => handleAction(row, kind)}
                />
              ))}
            </div>
          )}
        </div>
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
