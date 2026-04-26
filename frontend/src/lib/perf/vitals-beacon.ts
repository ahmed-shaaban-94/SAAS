/**
 * Web vitals beacon — collects FCP, LCP, CLS, INP and ships them to the
 * backend via navigator.sendBeacon so the POST does not block page unload.
 *
 * Usage: call `initVitals(pathname)` once in a client component after hydration.
 * The `route` argument should be the Next.js pathname (e.g. "/pos/terminal").
 */
import { onCLS, onFCP, onINP, onLCP } from "web-vitals";

const ENDPOINT = "/api/v1/perf/vitals";

function sendVital(name: string, value: number, route: string): void {
  if (typeof navigator === "undefined" || !navigator.sendBeacon) return;
  const payload = JSON.stringify({ metric: name, value, route, ts: Date.now() });
  navigator.sendBeacon(ENDPOINT, new Blob([payload], { type: "application/json" }));
}

export function initVitals(route: string): void {
  onFCP((m) => sendVital("FCP", m.value, route));
  onLCP((m) => sendVital("LCP", m.value, route));
  onCLS((m) => sendVital("CLS", m.value, route));
  onINP((m) => sendVital("INP", m.value, route));
}
