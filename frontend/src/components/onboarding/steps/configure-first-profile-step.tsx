"use client";

import { SlidersHorizontal } from "lucide-react";
import Link from "next/link";

interface ConfigureFirstProfileStepProps {
  onComplete: () => void;
}

export function ConfigureFirstProfileStep({
  onComplete,
}: ConfigureFirstProfileStepProps) {
  return (
    <div className="flex flex-col items-center text-center">
      <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-accent/10">
        <SlidersHorizontal className="h-12 w-12 text-accent" />
      </div>

      <h2 className="mb-2 text-xl font-semibold text-text-primary">
        Configure Pipeline Profile
      </h2>
      <p className="mb-6 max-w-sm text-sm text-text-secondary">
        Set up your first pipeline profile to define how your data maps to
        DataPulse&apos;s canonical schema.
      </p>

      <button
        onClick={onComplete}
        className="mb-3 flex w-full max-w-xs items-center justify-center rounded-lg bg-accent px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent/90"
      >
        Got it
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
