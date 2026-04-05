/**
 * PostHog analytics wrapper.
 *
 * Provides a thin abstraction over posthog-js so that analytics calls
 * are no-ops when the PostHog key is not configured (dev/test).
 */

import posthog from "posthog-js";

const POSTHOG_KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY ?? "";
const POSTHOG_HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST ?? "https://app.posthog.com";

let initialized = false;

export function initAnalytics(): void {
  if (initialized || !POSTHOG_KEY || typeof window === "undefined") return;

  posthog.init(POSTHOG_KEY, {
    api_host: POSTHOG_HOST,
    capture_pageview: true,
    capture_pageleave: true,
    persistence: "localStorage+cookie",
    autocapture: false,
    loaded: () => {
      initialized = true;
    },
  });
}

export function trackEvent(event: string, properties?: Record<string, unknown>): void {
  if (!POSTHOG_KEY) return;
  posthog.capture(event, properties);
}

export function identifyUser(
  userId: string,
  traits?: Record<string, unknown>,
): void {
  if (!POSTHOG_KEY) return;
  posthog.identify(userId, traits);
}

export function resetAnalytics(): void {
  if (!POSTHOG_KEY) return;
  posthog.reset();
}
