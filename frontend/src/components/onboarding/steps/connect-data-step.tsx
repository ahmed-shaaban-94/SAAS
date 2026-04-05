"use client";

import { Database, Upload } from "lucide-react";

interface ConnectDataStepProps {
  onComplete: () => void;
}

export function ConnectDataStep({ onComplete }: ConnectDataStepProps) {
  return (
    <div className="flex flex-col items-center text-center">
      <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-accent/10">
        <Database className="h-12 w-12 text-accent" />
      </div>

      <h2 className="mb-2 text-xl font-semibold text-text-primary">
        Connect Your Data
      </h2>
      <p className="mb-8 max-w-sm text-sm text-text-secondary">
        Upload your Excel/CSV files or use our sample dataset to get started.
      </p>

      <div className="flex w-full flex-col gap-3 sm:flex-row sm:justify-center">
        <button
          onClick={onComplete}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-accent px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent/90"
        >
          <Upload className="h-4 w-4" />
          Use Sample Data
        </button>
        <button
          onClick={onComplete}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-border bg-transparent px-6 py-2.5 text-sm font-medium text-text-secondary transition-colors hover:bg-divider"
        >
          I&apos;ll upload later
        </button>
      </div>
    </div>
  );
}
