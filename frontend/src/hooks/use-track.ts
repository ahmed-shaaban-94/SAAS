"use client";

import { useEffect } from "react";
import { trackEvent } from "@/lib/analytics";

/**
 * Fires a tracking event once when the component mounts.
 * Useful for page-view tracking.
 */
export function useTrack(
  event: string,
  properties?: Record<string, unknown>,
): void {
  useEffect(() => {
    trackEvent(event, properties);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [event]);
}
