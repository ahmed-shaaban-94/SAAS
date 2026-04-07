"use client";

import { WifiOff } from "lucide-react";

export default function OfflinePage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-page p-6">
      <div className="text-center">
        <WifiOff className="mx-auto h-16 w-16 text-text-secondary" />
        <h1 className="mt-6 text-2xl font-bold text-text-primary">
          You&apos;re Offline
        </h1>
        <p className="mt-2 text-sm text-text-secondary">
          Check your internet connection and try again.
        </p>
        <button
          onClick={() => window.location.reload()}
          className="mt-6 rounded-lg bg-accent px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent/90"
        >
          Retry
        </button>
      </div>
    </div>
  );
}
