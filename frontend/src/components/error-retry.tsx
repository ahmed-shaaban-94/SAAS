"use client";

import { AlertCircle, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

interface ErrorRetryProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorRetry({
  title = "Something went wrong",
  description = "Failed to load data. Please try again.",
  onRetry,
  className,
}: ErrorRetryProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center rounded-lg border border-border bg-card p-12", className)}>
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-growth-red/10">
        <AlertCircle className="h-6 w-6 text-growth-red" />
      </div>
      <h3 className="mt-4 text-lg font-medium text-text-primary">{title}</h3>
      <p className="mt-1 text-sm text-text-secondary">{description}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-page transition-colors hover:bg-accent/80"
        >
          <RefreshCw className="h-4 w-4" />
          Try Again
        </button>
      )}
    </div>
  );
}
