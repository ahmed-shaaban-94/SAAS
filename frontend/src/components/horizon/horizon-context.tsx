"use client";

/**
 * Horizon Mode — a dashboard-wide toggle that flips every KPI from its
 * "today" value to its forecasted value with a confidence band.
 *
 * The mode lives in a React context so every widget on the page can
 * react to the toggle. Components that opt in read the mode via the
 * `useHorizon()` hook and render the appropriate value + band.
 *
 * Persisted to sessionStorage so a refresh inside the same tab keeps the
 * user in their chosen mode. Cross-tab sync intentionally skipped —
 * horizon mode is a per-session exploration, not a long-lived setting.
 */

import { createContext, useCallback, useContext, useEffect, useState } from "react";

export type HorizonMode = "today" | "h30" | "h90";

export interface HorizonState {
  mode: HorizonMode;
  setMode: (mode: HorizonMode) => void;
  isForecast: boolean;
  daysOut: number;
}

const STORAGE_KEY = "dp_horizon_mode_v1";

const HorizonContext = createContext<HorizonState | null>(null);

function loadInitial(): HorizonMode {
  if (typeof window === "undefined") return "today";
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (raw === "today" || raw === "h30" || raw === "h90") return raw;
  } catch {
    // session storage unavailable — silent fallback
  }
  return "today";
}

export function HorizonProvider({ children }: { children: React.ReactNode }) {
  const [mode, setModeState] = useState<HorizonMode>(loadInitial);

  const setMode = useCallback((next: HorizonMode) => {
    setModeState(next);
    try {
      sessionStorage.setItem(STORAGE_KEY, next);
    } catch {
      // ignore
    }
  }, []);

  // Re-hydrate on mount for clients where initial render ran before
  // sessionStorage was accessible.
  useEffect(() => {
    const current = loadInitial();
    if (current !== mode) setModeState(current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const daysOut = mode === "h30" ? 30 : mode === "h90" ? 90 : 0;
  const isForecast = mode !== "today";

  return (
    <HorizonContext.Provider value={{ mode, setMode, isForecast, daysOut }}>
      {children}
    </HorizonContext.Provider>
  );
}

export function useHorizon(): HorizonState {
  const ctx = useContext(HorizonContext);
  if (!ctx) {
    // Permissive default so widgets can import the hook without forcing
    // every parent route to wrap itself in <HorizonProvider>.
    return { mode: "today", setMode: () => {}, isForecast: false, daysOut: 0 };
  }
  return ctx;
}
