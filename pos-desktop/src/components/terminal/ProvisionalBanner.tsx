import { CloudOff, AlertTriangle } from "lucide-react";
import { cn } from "@shared/lib/utils";

interface ProvisionalBannerProps {
  pending: number;
}

/**
 * Offline-mode banner shown directly below the header.
 *
 * Two visual modes depending on whether anything is queued yet:
 *
 *   - 0 queued    → cyan/info "Offline — sales will sync when network returns"
 *                   (calm; nothing has gone wrong yet)
 *   - N queued    → amber/warn "Offline — N transactions queued"
 *                   (something to reconcile when back online)
 *
 * The earlier copy ("Provisional mode — N queued") confused cashiers who
 * had no glossary entry for the word "provisional". The plain English
 * here matches what the receipt prints ("PENDING CONFIRMATION") and what
 * the K3 smoke-test step exercises.
 */
export function ProvisionalBanner({ pending }: ProvisionalBannerProps) {
  const hasQueued = pending > 0;
  return (
    <div
      role="status"
      data-testid="provisional-banner"
      className={cn(
        "flex items-center gap-2.5 border-b px-4 py-2 text-[12.5px] font-medium",
        hasQueued
          ? "border-amber-400/30 bg-amber-400/10 text-amber-200"
          : "border-cyan-400/30 bg-cyan-400/10 text-cyan-200",
      )}
    >
      {hasQueued ? (
        <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400" aria-hidden="true" />
      ) : (
        <CloudOff className="h-4 w-4 shrink-0 text-cyan-300" aria-hidden="true" />
      )}
      {hasQueued ? (
        <span>
          Offline — <span className="font-mono tabular-nums">{pending}</span>{" "}
          transaction{pending === 1 ? "" : "s"} queued, will sync when network returns
        </span>
      ) : (
        <span>Offline — sales will save here and sync when network returns</span>
      )}
    </div>
  );
}
