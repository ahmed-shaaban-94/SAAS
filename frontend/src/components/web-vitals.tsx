"use client";

/**
 * Web Vitals reporter — sends LCP, INP, CLS, FCP, TTFB metrics to Sentry.
 *
 * Uses Next.js's built-in `useReportWebVitals` hook (no extra package needed).
 * Rendered inside <Providers> so it activates on every page in the app shell.
 * The component renders nothing visible.
 */

import { useReportWebVitals } from "next/web-vitals";

export function WebVitals() {
  useReportWebVitals((metric) => {
    // Only report when Sentry DSN is configured
    if (!process.env.NEXT_PUBLIC_SENTRY_DSN) return;

    // Lazy-import Sentry to avoid loading it if DSN is missing
    import("@sentry/nextjs").then((Sentry) => {
      Sentry.withScope((scope) => {
        scope.setTag("vital_name", metric.name);
        scope.setContext("web_vital", {
          name: metric.name,
          value: metric.value,
          delta: metric.delta,
          id: metric.id,
        });
        Sentry.captureMessage(`Web Vital: ${metric.name}`, "info");
      });
    });
  });

  return null;
}
