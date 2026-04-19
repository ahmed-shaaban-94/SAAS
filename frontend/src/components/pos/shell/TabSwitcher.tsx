"use client";

import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

export type PosScreen = "terminal" | "sync" | "shift" | "drugs";

interface TabDef {
  id: PosScreen;
  kbd: string;
  labelKey: "terminal" | "sync" | "shift" | "drugs";
}

const TABS: readonly TabDef[] = [
  { id: "terminal", kbd: "F1", labelKey: "terminal" },
  { id: "sync", kbd: "F2", labelKey: "sync" },
  { id: "shift", kbd: "F3", labelKey: "shift" },
  { id: "drugs", kbd: "F4", labelKey: "drugs" },
] as const;

export interface TabSwitcherProps {
  screen: PosScreen;
  onSwitchScreen: (next: PosScreen) => void;
  /** Optional per-tab badge counts (e.g. `{ sync: 5 }` for unresolved issues). */
  badges?: Partial<Record<PosScreen, number>>;
}

/**
 * TabSwitcher — primary POS navigation row.
 *
 * Renders four tabs: Terminal (F1) / Sync (F2) / Shift (F3) / Drugs (F4).
 * The active tab is marked with `aria-current="page"` plus a cyan underline
 * and glow (see `docs/design/pos-terminal/frames/pos/shell.jsx`).
 */
export function TabSwitcher({ screen, onSwitchScreen, badges }: TabSwitcherProps) {
  const t = useTranslations("app.pos.tabs");

  return (
    <nav
      aria-label="POS primary navigation"
      className="flex flex-wrap items-center gap-1.5"
    >
      {TABS.map((tab) => {
        const active = screen === tab.id;
        const badge = badges?.[tab.id];
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onSwitchScreen(tab.id)}
            aria-current={active ? "page" : undefined}
            aria-label={`${t(tab.labelKey)} (${tab.kbd})`}
            className={cn(
              "inline-flex items-center gap-2 px-3 py-1.5",
              "rounded-[var(--pos-radius-btn,8px)]",
              "text-[12.5px] font-semibold transition-all duration-150",
              "border",
            )}
            style={{
              background: active ? "rgba(0, 199, 242, 0.12)" : "transparent",
              borderColor: active
                ? "rgba(0, 199, 242, 0.45)"
                : "var(--pos-line, rgba(255,255,255,0.06))",
              color: active
                ? "var(--pos-accent-hi, #5cdfff)"
                : "var(--pos-ink-2, #b8c0cc)",
              boxShadow: active ? "var(--pos-glow-cyan)" : undefined,
            }}
            data-active={active ? "true" : "false"}
          >
            <span>{t(tab.labelKey)}</span>
            <span
              className="pos-mono inline-flex items-center rounded-[4px] px-1.5 py-0.5 text-[10px]"
              style={{
                background: active
                  ? "rgba(0, 199, 242, 0.18)"
                  : "rgba(184, 192, 204, 0.08)",
                borderColor: active
                  ? "rgba(0, 199, 242, 0.35)"
                  : "var(--pos-line, rgba(255,255,255,0.06))",
                borderWidth: 1,
                borderStyle: "solid",
                color: active
                  ? "var(--pos-accent-hi, #5cdfff)"
                  : "var(--pos-ink-3, #7a8494)",
              }}
              aria-hidden="true"
            >
              {tab.kbd}
            </span>
            {typeof badge === "number" && badge > 0 ? (
              <span
                className="pos-mono inline-flex items-center rounded-full px-1.5 py-0.5 text-[9.5px] font-bold"
                style={{
                  background: "rgba(255, 123, 123, 0.15)",
                  color: "var(--pos-red, #ff7b7b)",
                  border: "1px solid rgba(255, 123, 123, 0.4)",
                }}
                aria-label={`${badge} pending`}
              >
                {badge}
              </span>
            ) : null}
          </button>
        );
      })}
    </nav>
  );
}
