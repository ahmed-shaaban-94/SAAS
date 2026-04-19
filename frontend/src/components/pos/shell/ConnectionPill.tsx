"use client";

import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

export interface ConnectionPillProps {
  online: boolean;
  queueDepth?: number;
}

/**
 * ConnectionPill — status chip shown in the TopBar right cluster.
 *
 * - `online=true`: green dot + "Online"
 * - `online=false` + `queueDepth>0`: amber star + "Provisional — N queued"
 * - `online=false` + `queueDepth=0`: amber star + "Provisional"
 *
 * Matches `docs/design/pos-terminal/frames/pos/shell.jsx` QueueChip.
 */
export function ConnectionPill({ online, queueDepth = 0 }: ConnectionPillProps) {
  const t = useTranslations("app.pos.connection");
  const isAmber = !online;
  const showQueue = !online && queueDepth > 0;

  if (!isAmber) {
    return (
      <div
        role="status"
        aria-live="polite"
        className={cn(
          "inline-flex items-center gap-1.5 rounded-[var(--pos-radius-chip,999px)] px-2.5 py-1",
          "text-[11px] font-semibold",
        )}
        style={{
          background: "rgba(29, 212, 139, 0.08)",
          border: "1px solid rgba(29, 212, 139, 0.3)",
          color: "var(--pos-green, #1dd48b)",
        }}
        data-variant="online"
      >
        <span
          aria-hidden="true"
          className="inline-block h-1.5 w-1.5 rounded-full"
          style={{ background: "var(--pos-green, #1dd48b)" }}
        />
        <span>{t("online")}</span>
      </div>
    );
  }

  const label = showQueue
    ? t("provisionalQueued", { count: queueDepth })
    : t("provisional");

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "inline-flex items-center gap-2 rounded-[var(--pos-radius-chip,999px)] px-2.5 py-1",
        "text-[11px] font-semibold",
      )}
      style={{
        background: "rgba(255, 171, 61, 0.1)",
        border: "1px solid rgba(255, 171, 61, 0.4)",
        color: "var(--pos-amber, #ffab3d)",
      }}
      data-variant={showQueue ? "provisional-queued" : "provisional"}
    >
      <svg
        width="12"
        height="12"
        viewBox="0 0 24 24"
        fill="none"
        aria-hidden="true"
      >
        <path
          d="M12 2 L14 10 L22 10 L16 15 L18 22 L12 18 L6 22 L8 15 L2 10 L10 10 Z"
          fill="currentColor"
          opacity="0.9"
        />
      </svg>
      <span>{label}</span>
    </div>
  );
}
