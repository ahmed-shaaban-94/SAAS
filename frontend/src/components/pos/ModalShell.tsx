"use client";

import { useEffect, type ReactNode } from "react";
import { FocusTrap } from "focus-trap-react";
import { cn } from "@/lib/utils";

/**
 * ModalShell — shared bottom-sheet wrapper for the design-recreation modals
 * (Voucher / Promotions / Insurance).
 *
 * Design source: docs/design/pos-terminal/frames/pos/modals.jsx
 *
 * Provides:
 * - Navy gradient background with accent-tinted ring-shadow
 * - 44×44 accent-tinted icon tile + Fraunces-italic title + uppercase badge
 * - Dismiss on Esc + backdrop click (both optional via `dismissOnBackdrop`)
 * - `dpFade` / `dpSlideUp` animations (declared in globals.css)
 *
 * Accessibility: role="dialog", aria-modal, aria-labelledby wired to the title.
 */
export type ModalAccent = "amber" | "purple" | "cyan" | "green";

const ACCENT_TO_TOKEN: Record<ModalAccent, string> = {
  amber: "var(--pos-amber, #ffab3d)",
  purple: "var(--pos-purple, #7467f8)",
  cyan: "var(--pos-accent, #00c7f2)",
  green: "var(--pos-green, #1dd48b)",
};

export interface ModalShellProps {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  /** Uppercase chip above the title (e.g. "VOUCHER"). */
  badge?: string;
  /** 22×22 SVG icon centred inside the 44×44 tile. */
  icon: ReactNode;
  accent?: ModalAccent;
  /** Max shell width in px. Default 520. */
  width?: number;
  /** If false, clicks on the backdrop do NOT close the modal. Default true. */
  dismissOnBackdrop?: boolean;
  children: ReactNode;
  /** id of the element used to label the dialog (defaults to the shell title). */
  titleId?: string;
  /** data-testid for the outer dialog wrapper. */
  testId?: string;
}

export function ModalShell({
  open,
  onClose,
  title,
  subtitle,
  badge,
  icon,
  accent = "cyan",
  width = 520,
  dismissOnBackdrop = true,
  children,
  titleId = "pos-modal-shell-title",
  testId,
}: ModalShellProps) {
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  const accentColor = ACCENT_TO_TOKEN[accent];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      data-testid={testId}
      onClick={dismissOnBackdrop ? onClose : undefined}
      className="fixed inset-0 z-[200] grid place-items-center"
      style={{
        background: "rgba(5,14,23,0.75)",
        backdropFilter: "blur(8px)",
        animation: "dpFade 200ms ease-out",
      }}
    >
      <FocusTrap
        focusTrapOptions={{
          escapeDeactivates: false, // Escape handled by window keydown listener above
          allowOutsideClick: true, // backdrop click must reach the backdrop handler
          initialFocus: false, // don't steal focus from typed input on open
        }}
      >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width,
          maxWidth: "92vw",
          maxHeight: "88vh",
          background:
            "linear-gradient(180deg, rgba(22,52,82,0.98), rgba(8,24,38,0.98))",
          border: "1px solid var(--pos-line-strong, rgba(255,255,255,0.12))",
          borderRadius: 18,
          boxShadow: `0 30px 80px rgba(0,0,0,0.6), 0 0 0 1px ${accentColor}22`,
          padding: 22,
          display: "flex",
          flexDirection: "column",
          gap: 14,
          animation: "dpSlideUp 280ms cubic-bezier(.2,.9,.3,1.1)",
          overflow: "hidden",
          color: "var(--pos-ink, #e8ecf2)",
        }}
      >
        <div className="flex items-start gap-3.5">
          <div
            aria-hidden="true"
            className="grid shrink-0 place-items-center"
            style={{
              width: 44,
              height: 44,
              borderRadius: 11,
              background: `color-mix(in oklab, ${accentColor} 18%, transparent)`,
              border: `1px solid ${accentColor}`,
              color: accentColor,
            }}
          >
            {icon}
          </div>
          <div className="min-w-0 flex-1">
            {badge && (
              <div
                className="font-mono"
                style={{
                  fontSize: 9.5,
                  fontWeight: 700,
                  letterSpacing: "0.22em",
                  color: accentColor,
                  textTransform: "uppercase",
                  marginBottom: 4,
                }}
              >
                {badge}
              </div>
            )}
            <div
              id={titleId}
              style={{
                fontFamily: "var(--font-fraunces), Fraunces, serif",
                fontSize: 20,
                fontWeight: 500,
                letterSpacing: "-0.01em",
              }}
            >
              {title}
            </div>
            {subtitle && (
              <div
                style={{
                  fontSize: 12.5,
                  color: "var(--pos-ink-3, #7a8494)",
                  marginTop: 3,
                }}
              >
                {subtitle}
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close (Esc)"
            data-testid="pos-modal-shell-close"
            className={cn(
              "flex items-center gap-1 rounded-md border px-2.5 py-1",
              "text-[11px] font-semibold",
            )}
            style={{
              borderColor: "var(--pos-line, rgba(255,255,255,0.06))",
              color: "var(--pos-ink-3, #7a8494)",
            }}
          >
            <span>Esc</span>
          </button>
        </div>
        <div className="min-h-0 overflow-y-auto">{children}</div>
      </div>
      </FocusTrap>
    </div>
  );
}
