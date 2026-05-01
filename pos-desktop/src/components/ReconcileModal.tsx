import { useState } from "react";
import { AlertTriangle, Loader2, RefreshCw, RotateCcw, X, XCircle } from "lucide-react";
import { reconcileQueue } from "@pos/lib/offline-db";
import type { ReconcileKind } from "@pos/lib/offline-db";
import type { QueueRow } from "@pos/lib/ipc";
import { cn } from "@shared/lib/utils";

interface ReconcileModalProps {
  row: QueueRow;
  kind: ReconcileKind;
  onSuccess: () => void;
  onCancel: () => void;
}

interface KindMeta {
  title: string;
  icon: typeof RefreshCw;
  iconClass: string;
  description: string;
  submitLabel: string;
  submitClass: string;
  requiresOverride: boolean;
}

const KIND_META: Record<ReconcileKind, KindMeta> = {
  retry_override: {
    title: "Retry with Override",
    icon: RefreshCw,
    iconClass: "text-accent",
    description:
      "Retry the rejected sync using a manager override code. The server re-verifies the code before committing.",
    submitLabel: "Retry with Override",
    submitClass: "bg-accent text-white hover:bg-accent/90",
    requiresOverride: true,
  },
  record_loss: {
    title: "Record as Loss",
    icon: XCircle,
    iconClass: "text-destructive",
    description:
      "Abandon this transaction as a loss. It will be marked reconciled and never re-sent to the server.",
    submitLabel: "Record as Loss",
    submitClass: "bg-destructive text-white hover:bg-destructive/90",
    requiresOverride: false,
  },
  corrective_void: {
    title: "Corrective Void",
    icon: RotateCcw,
    iconClass: "text-amber-400",
    description:
      "Issue a compensating void for a transaction that synced then was later rejected server-side.",
    submitLabel: "Issue Corrective Void",
    submitClass: "bg-amber-500 text-white hover:bg-amber-500/90",
    requiresOverride: false,
  },
};

function isValidOverride(code: string): boolean {
  return /^[A-Za-z0-9]{6}$/.test(code.trim());
}

export function ReconcileModal({ row, kind, onSuccess, onCancel }: ReconcileModalProps) {
  const meta = KIND_META[kind];
  const Icon = meta.icon;

  const [note, setNote] = useState("");
  const [overrideCode, setOverrideCode] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const noteValid = note.trim().length >= 3;
  const overrideValid = !meta.requiresOverride || isValidOverride(overrideCode);
  const canSubmit = noteValid && overrideValid && !isLoading;

  async function handleSubmit() {
    if (!noteValid) {
      setError("Note must be at least 3 characters");
      return;
    }
    if (meta.requiresOverride && !overrideValid) {
      setError("Override code must be 6 alphanumeric characters");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      await reconcileQueue(
        row.local_id,
        kind,
        note.trim(),
        meta.requiresOverride ? overrideCode.trim() : null,
      );
      onSuccess();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to reconcile");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="reconcile-modal-title"
    >
      <div className="w-full max-w-md rounded-2xl border border-border bg-surface shadow-2xl">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div className="flex items-center gap-2">
            <Icon className={cn("h-4 w-4", meta.iconClass)} />
            <span id="reconcile-modal-title" className="text-sm font-semibold text-text-primary">
              {meta.title}
            </span>
          </div>
          <button
            type="button"
            onClick={onCancel}
            aria-label="Close"
            className="rounded-lg p-1 text-text-secondary hover:bg-surface-raised"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4 p-4">
          <div className="rounded-xl border border-border bg-surface-raised p-3">
            <p className="text-xs text-text-secondary">Endpoint</p>
            <p className="truncate font-mono text-xs text-text-primary">{row.endpoint}</p>
            <p className="mt-2 text-xs text-text-secondary">Client txn id</p>
            <p className="truncate font-mono text-xs text-text-primary">{row.client_txn_id}</p>
          </div>

          {row.last_error && (
            <div
              className="rounded-xl border border-destructive/30 bg-destructive/10 p-3"
              role="alert"
            >
              <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-destructive">
                <AlertTriangle className="h-3 w-3" />
                Last error
              </div>
              <p className="break-words text-xs text-destructive">{row.last_error}</p>
            </div>
          )}

          <p className="text-xs text-text-secondary">{meta.description}</p>

          {meta.requiresOverride && (
            <div>
              <label
                htmlFor="reconcile-override"
                className="mb-1 block text-xs font-medium text-text-secondary"
              >
                Manager Override Code <span className="text-destructive">*</span>
              </label>
              <input
                id="reconcile-override"
                type="text"
                inputMode="text"
                autoComplete="off"
                maxLength={6}
                value={overrideCode}
                onChange={(e) => setOverrideCode(e.target.value.toUpperCase())}
                placeholder="6-char code"
                className={cn(
                  "w-full rounded-xl border border-border bg-surface px-3 py-2",
                  "text-sm font-mono tracking-widest text-text-primary placeholder:text-text-secondary",
                  "focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent",
                )}
              />
            </div>
          )}

          <div>
            <label
              htmlFor="reconcile-note"
              className="mb-1 block text-xs font-medium text-text-secondary"
            >
              Note <span className="text-destructive">*</span>
            </label>
            <textarea
              id="reconcile-note"
              rows={3}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Why is this being reconciled?"
              className={cn(
                "w-full resize-none rounded-xl border border-border bg-surface px-3 py-2",
                "text-sm text-text-primary placeholder:text-text-secondary",
                "focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent",
              )}
            />
          </div>

          {error && (
            <p className="text-xs text-destructive" role="alert">
              {error}
            </p>
          )}

          <div className="flex gap-2">
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 rounded-xl border border-border py-2.5 text-sm font-medium text-text-secondary hover:bg-surface-raised"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!canSubmit}
              className={cn(
                "flex flex-1 items-center justify-center gap-2 rounded-xl py-2.5",
                "text-sm font-semibold",
                meta.submitClass,
                "disabled:pointer-events-none disabled:opacity-40",
              )}
            >
              {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
              {meta.submitLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
