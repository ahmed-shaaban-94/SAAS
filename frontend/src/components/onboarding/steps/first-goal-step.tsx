"use client";

import { Target } from "lucide-react";
import { useState } from "react";

interface FirstGoalStepProps {
  onComplete: () => void;
}

function formatWithCommas(value: string): string {
  const digits = value.replace(/[^0-9]/g, "");
  if (!digits) return "";
  return Number(digits).toLocaleString("en-US");
}

export function FirstGoalStep({ onComplete }: FirstGoalStepProps) {
  const [target, setTarget] = useState("");

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setTarget(formatWithCommas(e.target.value));
  };

  return (
    <div className="flex flex-col items-center text-center">
      <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-accent/10">
        <Target className="h-12 w-12 text-accent" />
      </div>

      <h2 className="mb-2 text-xl font-semibold text-text-primary">
        Set Your First Goal
      </h2>
      <p className="mb-6 max-w-sm text-sm text-text-secondary">
        Set a revenue target to track your progress.
      </p>

      <div className="mb-4 w-full max-w-xs">
        <label
          htmlFor="revenue-target"
          className="mb-1.5 block text-left text-xs font-medium text-text-secondary"
        >
          Monthly Revenue Target
        </label>
        <div className="relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-text-secondary">
            $
          </span>
          <input
            id="revenue-target"
            type="text"
            inputMode="numeric"
            value={target}
            onChange={handleChange}
            placeholder="100,000"
            className="w-full rounded-lg border border-border bg-transparent py-2.5 pl-7 pr-3 text-sm text-text-primary placeholder:text-text-secondary/50 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
          />
        </div>
      </div>

      <button
        onClick={onComplete}
        disabled={!target}
        className="mb-3 w-full max-w-xs rounded-lg bg-accent px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-50"
      >
        Set Goal
      </button>

      <button
        onClick={onComplete}
        className="text-xs text-text-secondary transition-colors hover:text-text-primary"
      >
        Skip for now
      </button>
    </div>
  );
}
