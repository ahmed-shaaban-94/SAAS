/**
 * Golden-Path End-to-End + CI TTFI Gate (Phase 2 Task 6 / #405).
 *
 * Walks a brand-new tenant through the full golden path:
 *   /upload  →  "Use sample pharma data" CTA
 *            →  redirect /dashboard?first_upload=1
 *            →  first-insight card visible with non-empty title
 *   …and asserts that TTFI (upload_started → first_insight_seen) is
 *   strictly less than 5 minutes.
 *
 * Backend is mocked via `page.route`:
 *   POST /api/v1/onboarding/load-sample  → synthetic 5 k row result
 *   GET  /api/v1/insights/first          → synthetic pharma insight
 *
 * TTFI is captured from the `ttfi:event` CustomEvent emitted by
 * `frontend/src/lib/analytics-events.ts` so the measurement is
 * independent of PostHog availability. Failure artifacts (trace,
 * screenshot, video) are uploaded by Playwright's default reporter
 * when the assertion breaks.
 */

import { test, expect, type Page } from "@playwright/test";

/** Hard CI gate: TTFI must stay under this threshold. */
const TTFI_LIMIT_MS = 5 * 60 * 1000;

const MOCK_SAMPLE_LOAD = {
  rows_loaded: 5000,
  pipeline_run_id: "golden-path-run-1",
  duration_seconds: 4.2,
};

const MOCK_FIRST_INSIGHT = {
  insight: {
    kind: "top_seller" as const,
    title: "Your top seller: Paracetamol 500mg Tab",
    body: "drove $12,450 in the last 30 days",
    action_href: "/products",
    confidence: 0.72,
  },
};

interface CapturedEvent {
  name: string;
  at: number;
}

/**
 * Subscribe to the ttfi:event CustomEvent stream. Must be installed
 * before `page.goto()` so the init-script runs on the first navigation.
 */
async function installTtfiObserver(page: Page): Promise<CapturedEvent[]> {
  const captured: CapturedEvent[] = [];

  await page.exposeFunction("__goldenPathRecord", (name: string) => {
    captured.push({ name, at: Date.now() });
  });

  await page.addInitScript(() => {
    window.addEventListener("ttfi:event", (e: Event) => {
      const detail = (e as CustomEvent).detail as { name?: string } | undefined;
      if (!detail?.name) return;
      (
        window as unknown as { __goldenPathRecord: (n: string) => void }
      ).__goldenPathRecord(detail.name);
    });
  });

  // Keep PostHog and any analytics beacons off the network even if a key leaks in.
  await page.route(/posthog\.com/, (route) =>
    route.fulfill({ status: 200, body: "{}" }),
  );

  return captured;
}

test.describe("Golden Path — upload to first-insight in < 5 min", () => {
  test("sample CTA → dashboard → first-insight card visible, TTFI gate holds", async ({
    page,
  }) => {
    const captured = await installTtfiObserver(page);

    // Mock the two endpoints the golden path actually depends on.
    await page.route("**/api/v1/onboarding/load-sample", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_SAMPLE_LOAD),
      }),
    );
    await page.route("**/api/v1/insights/first", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_FIRST_INSIGHT),
      }),
    );

    // 1. Land on /upload — this fires upload_started.
    await page.goto("/upload");
    await expect(
      page.getByRole("button", { name: /use sample pharma data/i }),
    ).toBeVisible({ timeout: 15000 });

    // 2. Click the sample CTA — fires upload_completed after the endpoint
    //    resolves, then navigates to the dashboard.
    await page
      .getByRole("button", { name: /use sample pharma data/i })
      .click();

    // 3. Wait for the dashboard redirect with the first_upload flag.
    await page.waitForURL(/\/dashboard\?first_upload=1/, { timeout: 15000 });

    // 4. First-insight card must render with the mocked title — this is
    //    what fires first_insight_seen.
    await expect(
      page.getByText(MOCK_FIRST_INSIGHT.insight.title),
    ).toBeVisible({ timeout: 15000 });

    // Give the event loop a tick so the listener has definitely recorded.
    await page.waitForTimeout(200);

    // 5. Assert the onboarding strip auto-completed the three events.
    const orderedEvents = captured.map((e) => e.name);
    expect(orderedEvents).toContain("upload_started");
    expect(orderedEvents).toContain("upload_completed");
    expect(orderedEvents).toContain("first_insight_seen");

    // 6. The real gate: TTFI < 5 minutes.
    const started = captured.find((e) => e.name === "upload_started");
    const insightSeen = captured.find((e) => e.name === "first_insight_seen");
    expect(started, "upload_started must fire").toBeTruthy();
    expect(insightSeen, "first_insight_seen must fire").toBeTruthy();
    const ttfiMs = insightSeen!.at - started!.at;
    // eslint-disable-next-line no-console
    console.log(`Golden-path TTFI: ${ttfiMs} ms (limit ${TTFI_LIMIT_MS} ms)`);
    expect(
      ttfiMs,
      `TTFI regressed: ${ttfiMs} ms ≥ ${TTFI_LIMIT_MS} ms limit`,
    ).toBeLessThan(TTFI_LIMIT_MS);
  });
});
