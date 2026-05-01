import { useEffect } from "react";
import { cn } from "@shared/lib/utils";
import {
  SHORTCUTS,
  TONE_COLOR,
  type Shortcut,
} from "@pos/components/terminal/ShortcutLegend";

/** Additional modal-level shortcuts shown only in the cheat-sheet overlay. */
const MODAL_SHORTCUTS = [
  { key: "Esc", label: "Close modal", tone: "default" as const },
  { key: "Enter", label: "Confirm modal", tone: "cyan" as const },
  { key: "?", label: "Toggle this overlay", tone: "default" as const },
];

interface ShortcutsCheatSheetProps {
  open: boolean;
  onClose: () => void;
}

/**
 * Full-screen overlay listing all POS keyboard shortcuts.
 * Open/close with `?` from the terminal page. Also dismisses on Esc.
 */
export function ShortcutsCheatSheet({ open, onClose }: ShortcutsCheatSheetProps) {
  useEffect(() => {
    if (!open) return;
    function handler(e: KeyboardEvent) {
      const target = e.target as HTMLElement | null;
      const isInput =
        !!target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.hasAttribute?.("data-pos-scanner-ignore"));
      if (isInput) return;

      if (e.key === "Escape" || e.key === "?") {
        e.preventDefault();
        onClose();
      }
    }
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Keyboard shortcuts"
      data-pos-scanner-ignore
      onClick={onClose}
      className="fixed inset-0 z-[300] grid place-items-center"
      style={{
        background: "rgba(5,14,23,0.82)",
        backdropFilter: "blur(10px)",
        animation: "dpFade 180ms ease-out",
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 560,
          maxWidth: "92vw",
          maxHeight: "88vh",
          background:
            "linear-gradient(180deg, rgba(22,52,82,0.98), rgba(8,24,38,0.98))",
          border: "1px solid var(--pos-line-strong, rgba(255,255,255,0.12))",
          borderRadius: 18,
          boxShadow:
            "0 30px 80px rgba(0,0,0,0.6), 0 0 0 1px rgba(0,199,242,0.15)",
          padding: 24,
          display: "flex",
          flexDirection: "column",
          gap: 18,
          animation: "dpSlideUp 260ms cubic-bezier(.2,.9,.3,1.1)",
          overflow: "hidden auto",
          color: "var(--pos-ink, #e8ecf2)",
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <div
              className="font-mono text-[9.5px] font-bold uppercase tracking-[0.22em]"
              style={{ color: "var(--pos-accent, #00c7f2)", marginBottom: 4 }}
            >
              POS SHORTCUTS
            </div>
            <div
              style={{
                fontFamily: "var(--font-fraunces), Fraunces, serif",
                fontSize: 20,
                fontWeight: 500,
                letterSpacing: "-0.01em",
              }}
            >
              Keyboard quick reference
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close shortcuts (Esc or ?)"
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

        {/* Terminal shortcuts */}
        <section>
          <div
            className="mb-2 font-mono text-[10px] font-bold uppercase tracking-wider"
            style={{ color: "var(--pos-ink-3, #7a8494)" }}
          >
            Terminal
          </div>
          <div className="grid grid-cols-2 gap-2">
            {SHORTCUTS.map(({ key, label, tone = "default" }: Shortcut) => (
              <div key={key} className="flex items-center gap-2" style={{ fontSize: 12 }}>
                <kbd
                  className={cn(
                    "grid min-h-[22px] min-w-[38px] place-items-center rounded border px-1.5",
                    "font-mono text-[10px] font-semibold",
                    "border-[rgba(255,255,255,0.1)] bg-[rgba(255,255,255,0.06)]",
                    TONE_COLOR[tone],
                  )}
                >
                  {key}
                </kbd>
                <span style={{ color: "var(--pos-ink-2, #a8b3c4)" }}>{label}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Modal shortcuts */}
        <section>
          <div
            className="mb-2 font-mono text-[10px] font-bold uppercase tracking-wider"
            style={{ color: "var(--pos-ink-3, #7a8494)" }}
          >
            Inside modals
          </div>
          <div className="grid grid-cols-2 gap-2">
            {MODAL_SHORTCUTS.map(({ key, label, tone = "default" }: Shortcut) => (
              <div key={key} className="flex items-center gap-2" style={{ fontSize: 12 }}>
                <kbd
                  className={cn(
                    "grid min-h-[22px] min-w-[38px] place-items-center rounded border px-1.5",
                    "font-mono text-[10px] font-semibold",
                    "border-[rgba(255,255,255,0.1)] bg-[rgba(255,255,255,0.06)]",
                    TONE_COLOR[tone],
                  )}
                >
                  {key}
                </kbd>
                <span style={{ color: "var(--pos-ink-2, #a8b3c4)" }}>{label}</span>
              </div>
            ))}
          </div>
        </section>

        <p
          className="text-center font-mono text-[10px]"
          style={{ color: "var(--pos-ink-3, #7a8494)" }}
        >
          Press <kbd className="rounded border border-[rgba(255,255,255,0.1)] bg-[rgba(255,255,255,0.06)] px-1 font-mono">?</kbd> or <kbd className="rounded border border-[rgba(255,255,255,0.1)] bg-[rgba(255,255,255,0.06)] px-1 font-mono">Esc</kbd> to close
        </p>
      </div>
    </div>
  );
}
