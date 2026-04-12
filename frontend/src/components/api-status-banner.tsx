"use client";

import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";

interface ApiStatusBannerProps {
  isApiDown: boolean;
  isRecovering: boolean;
}

export function ApiStatusBanner({ isApiDown, isRecovering }: ApiStatusBannerProps) {
  if (isRecovering) {
    return (
      <div className="border-b border-growth-green/30 bg-growth-green/10 px-4 py-2 text-center text-sm text-growth-green">
        <CheckCircle2 className="mr-1.5 inline-block h-4 w-4" />
        Connection restored — data is refreshing.
      </div>
    );
  }

  if (isApiDown) {
    return (
      <div className="border-b border-amber-500/30 bg-amber-500/10 px-4 py-2 text-center text-sm text-amber-400">
        <AlertCircle className="mr-1.5 inline-block h-4 w-4" />
        API connection issue — retrying automatically
        <Loader2 className="ml-1.5 inline-block h-3.5 w-3.5 animate-spin" />
      </div>
    );
  }

  return null;
}
