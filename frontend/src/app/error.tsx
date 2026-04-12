"use client";

import { AlertTriangle } from "lucide-react";
import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production") {
      console.error("Unhandled error:", error);
    }
  }, [error]);
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center">
      <AlertTriangle className="h-16 w-16 text-growth-red" />
      <h1 className="mt-6 text-2xl font-bold">Something went wrong</h1>
      <p className="mt-2 text-sm text-text-secondary">
        {process.env.NODE_ENV !== "production"
          ? error.message || "An unexpected error occurred"
          : "An unexpected error occurred. Please try again."}
      </p>
      <button
        onClick={reset}
        className="mt-6 rounded-lg bg-accent px-6 py-2.5 text-sm font-medium text-page hover:bg-accent/90 transition-colors"
      >
        Try again
      </button>
    </div>
  );
}
