"use client";

/**
 * Horizon Mode toggle — three-way pill group:
 *   Today  |  Horizon 30d  |  Horizon 90d
 *
 * When a forecast mode is active, the toggle glows purple (to match the
 * forecast accent used in widgets) and the dashboard re-renders with
 * forecasted values + confidence bands.
 */

import { useHorizon, type HorizonMode } from "./horizon-context";
import "./horizon-toggle.css";

const OPTIONS: Array<{ id: HorizonMode; label: string; forecast?: boolean }> = [
  { id: "today", label: "Today" },
  { id: "h30", label: "Horizon · 30d", forecast: true },
  { id: "h90", label: "Horizon · 90d", forecast: true },
];

export function HorizonToggle() {
  const { mode, setMode } = useHorizon();

  return (
    <div
      className="horizon-toggle"
      role="group"
      aria-label="Horizon mode — switch between today's values and forecasted values"
    >
      {OPTIONS.map((opt) => {
        const active = mode === opt.id;
        return (
          <button
            key={opt.id}
            type="button"
            aria-pressed={active}
            className={opt.forecast && active ? "forecast" : undefined}
            onClick={() => setMode(opt.id)}
          >
            {opt.forecast && active && <span className="dot" />}
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
