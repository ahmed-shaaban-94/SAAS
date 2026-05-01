import { cn } from "@shared/lib/utils";

export interface Shortcut {
  key: string;
  label: string;
  tone?: "cyan" | "amber" | "purple" | "green" | "default";
}

export const TONE_COLOR: Record<NonNullable<Shortcut["tone"]>, string> = {
  default: "text-text-primary",
  cyan: "text-cyan-300",
  amber: "text-amber-300",
  purple: "text-violet-300",
  green: "text-emerald-300",
};

// F12 removed — was a duplicate of F7 (voucher) and collided with the
// layout-level void-transaction dispatch. Single shortcut per function.
export const SHORTCUTS: Shortcut[] = [
  { key: "F1", label: "Terminal", tone: "cyan" },
  { key: "F2", label: "Sync", tone: "amber" },
  { key: "F7", label: "Voucher", tone: "amber" },
  { key: "F9", label: "Cash", tone: "green" },
  { key: "F10", label: "Card", tone: "cyan" },
  { key: "F11", label: "Insurance", tone: "purple" },
  // Quick-pick fires only when no input is focused. The scan bar
  // auto-focuses on mount, so cashiers press Esc/Tab away from it
  // first. Wording is explicit so the legend doesn't lie.
  { key: "1–9", label: "Quick pick (outside scan)" },
  { key: "/", label: "Focus search" },
  { key: "Enter", label: "Charge", tone: "cyan" },
  { key: "Esc", label: "Cancel" },
];

/** Keyboard shortcut legend rendered next to the keypad. */
export function ShortcutLegend() {
  return (
    <div
      className={cn(
        "rounded-xl border border-[var(--pos-line)] bg-[rgba(8,24,38,0.5)] p-3",
      )}
    >
      <div className="mb-2 font-mono text-[10px] font-bold uppercase tracking-wider text-text-secondary">
        Shortcuts
      </div>
      <div className="grid grid-cols-2 gap-1.5 text-[11px]">
        {SHORTCUTS.map(({ key, label, tone = "default" }) => (
          <div key={key} className="flex items-center gap-1.5 text-text-secondary">
            <kbd
              className={cn(
                "grid h-5 min-w-[34px] place-items-center rounded border border-border bg-surface-raised px-1",
                "font-mono text-[10px] font-semibold",
                TONE_COLOR[tone],
              )}
            >
              {key}
            </kbd>
            <span className="truncate">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
