"use client";

import { createContext, useContext, useState, type ReactNode } from "react";
import { ArrowLeftRight } from "lucide-react";
import { ComparisonPanel } from "./comparison-panel";

const CompareContext = createContext<{
  active: boolean;
  toggle: () => void;
  close: () => void;
}>({ active: false, toggle: () => {}, close: () => {} });

/** Wrap the dashboard section that contains both the button and the panel. */
export function CompareProvider({ children }: { children: ReactNode }) {
  const [active, setActive] = useState(false);
  return (
    <CompareContext.Provider
      value={{
        active,
        toggle: () => setActive((v) => !v),
        close: () => setActive(false),
      }}
    >
      {children}
    </CompareContext.Provider>
  );
}

/** The toggle button — place in the header actions area. */
export function CompareButton() {
  const { active, toggle } = useContext(CompareContext);
  return (
    <button
      onClick={toggle}
      className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-all ${
        active
          ? "bg-accent/10 text-accent"
          : "text-text-secondary hover:bg-accent/10 hover:text-accent"
      }`}
    >
      <ArrowLeftRight className="h-4 w-4" />
      Compare
    </button>
  );
}

/** The comparison panel — place between FilterBar and DashboardContent. */
export function ComparePanel() {
  const { active, close } = useContext(CompareContext);
  if (!active) return null;
  return <ComparisonPanel onClose={close} />;
}
