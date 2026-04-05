"use client";

import { createContext, useContext, useState, useCallback, type ReactNode } from "react";

interface CrosshairState {
  /** The active data index being hovered (null = nothing hovered) */
  activeIndex: number | null;
  /** Which chart triggered the crosshair (to avoid re-triggering self) */
  sourceId: string | null;
}

interface CrosshairContextValue {
  state: CrosshairState;
  setActive: (index: number | null, sourceId: string) => void;
  clear: () => void;
}

const CrosshairContext = createContext<CrosshairContextValue | null>(null);

export function CrosshairProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<CrosshairState>({
    activeIndex: null,
    sourceId: null,
  });

  const setActive = useCallback((index: number | null, sourceId: string) => {
    setState({ activeIndex: index, sourceId });
  }, []);

  const clear = useCallback(() => {
    setState({ activeIndex: null, sourceId: null });
  }, []);

  return (
    <CrosshairContext.Provider value={{ state, setActive, clear }}>
      {children}
    </CrosshairContext.Provider>
  );
}

export function useCrosshair() {
  const ctx = useContext(CrosshairContext);
  if (!ctx) {
    // Graceful fallback if used outside provider
    return {
      state: { activeIndex: null, sourceId: null } as CrosshairState,
      setActive: () => {},
      clear: () => {},
    };
  }
  return ctx;
}
