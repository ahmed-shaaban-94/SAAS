/**
 * Golden-Path End-to-End + CI TTFI Gate (Phase 2 Task 6 / #405).
 * Updated by Follow-up 1b to hit the real backend — no page.route() mocks.
 *
 * Walks a brand-new tenant through the full golden path:
 *   /upload  →  "Use sample pharma data" CTA
 *            →  redirect /dashboard?first_upload=1
 *            →  first-insight card visible with non-empty title
 *   …and asserts that TTFI (upload_started → first_insight_seen) is
 *   strictly less than 5 minutes.
 *
 * All requests reach the real backend (POST /api/v1/onboarding/load-sample
 * and GET /api/v1/insights/first are NOT mocked) so the numbers reflect
 * true pipeline latency.
 *
 * TTFI is captured from the `ttfi:event` CustomEvent emitted by
 * `frontend/src/lib/analytics-events.ts` so the measurement is
 * independent of PostHog availability. Failure artifacts (trace,
 * screenshot, video) are uploaded by Playwright's default reporter
 * when the assertion breaks.
 */

import { test, expect, type Page } from "@playwright/test";

/** Hard CI gate: TTFI must stay under this threshold (real backend — allow up to 5 min). */
const TTFI_LIMIT_MS = 5 * 60 * 1000;

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
    //    Real pipeline may take several seconds — use a generous timeout.
    await page.waitForURL(/\/dashboard\?first_upload=1/, { timeout: 90000 });

    // 4. First-insight card must be visible and contain a non-empty title.
    //    Use data-testid locators (same pattern as golden-path-real-backend.spec.ts)
    //    rather than the mocked title string — this fires first_insight_seen.
    const insightCard = page.locator("[data-testid='first-insight-card']");
    await expect(insightCard).toBeVisible({ timeout: 120000 });
    const cardTitle = insightCard.locator("[data-testid='insight-title']");
    await expect(cardTitle).not.toBeEmpty({ timeout: 10000 });

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
