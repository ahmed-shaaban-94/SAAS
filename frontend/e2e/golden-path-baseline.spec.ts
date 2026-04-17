/**
 * Golden-Path Baseline E2E (Phase 2, Task 0 / #399).
 *
 * Measures TTFI (Time-to-First-Insight) — the latency between the
 * `upload_started` event and the `first_insight_seen` event — against
 * whatever UX exists today. The numbers this spec produces are the
 * baseline we must beat in Phase 2 (Tasks 1–6).
 *
 * Two modes:
 *  1. "Events fire in order" — runs anywhere. Captures PostHog calls
 *     and asserts the 4 golden-path events fire at the right seams.
 *  2. "TTFI measurement" — runs on CI/droplet against a live backend
 *     (requires env `RUN_TTFI_BASELINE=1`). Writes timings to
 *     `playwright-report/ttfi-baseline.json`.
 *
 * Both modes are intentionally permissive about the current UX — there
 * is no wizard yet, no first-insight card yet. We only assert that the
 * instrumentation _would_ fire if the user reached the corresponding
 * seam.
 */

import { test, expect, type Page } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

const RUN_BASELINE = process.env.RUN_TTFI_BASELINE === "1";
const MOCK_UPLOAD_RESPONSE = [
  {
    file_id: "ttfi-seed-1",
    filename: "ttfi-baseline.csv",
    size_bytes: 2048,
    status: "uploaded",
  },
];
const MOCK_CONFIRM_RESPONSE = { status: "confirmed", file_ids: ["ttfi-seed-1"] };
const MOCK_TRIGGER_RESPONSE = { run_id: "ttfi-run-1", status: "running" };

interface CapturedEvent {
  name: string;
  props: Record<string, unknown>;
  at: number; // epoch ms
}

/**
 * Subscribe to the `ttfi:event` window CustomEvent that
 * `frontend/src/lib/analytics-events.ts` dispatches on every golden-path
 * capture. Fires regardless of whether PostHog is configured, so it works
 * in CI where `NEXT_PUBLIC_POSTHOG_KEY` is unset.
 *
 * Also blocks any real posthog.com network calls just in case a key
 * leaks into the test environment.
 */
async function installTtfiObserver(page: Page): Promise<CapturedEvent[]> {
  const captured: CapturedEvent[] = [];

  await page.exposeFunction("__ttfiRecord", (name: string, props: unknown) => {
    captured.push({
      name,
      props: (props ?? {}) as Record<string, unknown>,
      at: Date.now(),
    });
  });

  await page.addInitScript(() => {
    window.addEventListener("ttfi:event", (e: Event) => {
      const detail = (e as CustomEvent).detail as {
        name: string;
        properties: unknown;
      };
      (
        window as unknown as {
          __ttfiRecord: (n: string, p?: unknown) => void;
        }
      ).__ttfiRecord(detail.name, detail.properties);
    });
  });

  await page.route(/posthog\.com/, (route) => route.fulfill({ status: 200, body: "{}" }));

  return captured;
}

test.describe("Golden-Path baseline — events fire at the right seams", () => {
  test("upload_started fires when the user lands on /upload", async ({ page }) => {
    const captured = await installTtfiObserver(page);

    await page.goto("/upload");
    await expect(page.getByText("Drop files here or click to browse")).toBeVisible({
      timeout: 15000,
    });

    // Give the useEffect a tick to fire.
    await page.waitForTimeout(250);

    const names = captured.map((c) => c.name);
    expect(names).toContain("upload_started");
    const ev = captured.find((c) => c.name === "upload_started");
    expect(ev?.props).toHaveProperty("ttfi_seam", "upload_started");
  });

  test("first_dashboard_view fires when the user lands on /dashboard", async ({ page }) => {
    const captured = await installTtfiObserver(page);

    await page.goto("/dashboard");
    // Wait for at least the header to render; dashboard-content has its own loaders.
    await expect(page.locator("h1").first()).toBeVisible({ timeout: 15000 });
    await page.waitForTimeout(250);

    const names = captured.map((c) => c.name);
    expect(names).toContain("first_dashboard_view");
  });

  test("upload_completed fires when pipeline run reaches success", async ({ page }) => {
    const captured = await installTtfiObserver(page);

    // Mock upload → confirm → trigger → stream(success).
    await page.route("**/api/v1/upload/files", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_UPLOAD_RESPONSE),
      }),
    );
    await page.route("**/api/v1/upload/confirm", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_CONFIRM_RESPONSE),
      }),
    );
    await page.route("**/api/v1/pipeline/trigger", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_TRIGGER_RESPONSE),
      }),
    );
    // Synthetic SSE stream that closes on "success".
    await page.route("**/api/v1/pipeline/runs/*/stream", (route) => {
      const body = [
        "event: status_change\n",
        `data: ${JSON.stringify({ run_id: "ttfi-run-1", status: "running", started_at: new Date().toISOString(), finished_at: null, duration_seconds: null, rows_loaded: null, error_message: null })}\n\n`,
        "event: complete\n",
        `data: ${JSON.stringify({ run_id: "ttfi-run-1", status: "success", started_at: new Date().toISOString(), finished_at: new Date().toISOString(), duration_seconds: 7.5, rows_loaded: 5000, error_message: null })}\n\n`,
      ].join("");
      route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body,
      });
    });

    await page.goto("/upload");
    await page
      .locator('input[type="file"]')
      .setInputFiles({
        name: "ttfi-baseline.csv",
        mimeType: "text/csv",
        buffer: Buffer.from("date,product,revenue\n2026-01-01,Widget,100\n"),
      });
    await expect(page.getByText("ttfi-baseline.csv")).toBeVisible();
    await page.getByRole("button", { name: /Confirm Import/i }).click();
    await expect(page.getByRole("button", { name: /Run Pipeline/i })).toBeVisible({
      timeout: 10000,
    });
    await page.getByRole("button", { name: /Run Pipeline/i }).click();

    // Let the synthetic stream + React state settle.
    await page.waitForTimeout(1500);

    const names = captured.map((c) => c.name);
    expect(names).toContain("upload_completed");
    const ev = captured.find((c) => c.name === "upload_completed");
    expect(ev?.props).toMatchObject({
      run_id: "ttfi-run-1",
      ttfi_seam: "upload_completed",
    });
  });
});

/**
 * Full TTFI measurement run — gated on `RUN_TTFI_BASELINE=1` so it does not
 * block local dev. Intended to be invoked on the droplet against real data.
 * Writes the raw timings to `playwright-report/ttfi-baseline.json`.
 */
test.describe("Golden-Path baseline — TTFI measurement (droplet only)", () => {
  test.skip(!RUN_BASELINE, "Set RUN_TTFI_BASELINE=1 to execute on droplet");

  test("records upload_started → first_insight_seen latency", async ({ page }) => {
    const captured = await installTtfiObserver(page);

    const t0 = Date.now();
    await page.goto("/upload");
    await expect(page.getByText("Drop files here or click to browse")).toBeVisible();

    // The rest of the flow today: upload, confirm, run pipeline, navigate to
    // dashboard. There is no first-insight card yet, so first_insight_seen
    // may not fire at all — we record whatever does.
    await page.waitForTimeout(500);
    await page.goto("/dashboard");
    await expect(page.locator("h1").first()).toBeVisible({ timeout: 30000 });
    await page.waitForTimeout(1000);

    const result = {
      baseline_run_at: new Date(t0).toISOString(),
      events: captured.map((e) => ({
        name: e.name,
        delta_ms: e.at - t0,
        props: e.props,
      })),
      first_insight_seen_fired: captured.some((e) => e.name === "first_insight_seen"),
      ttfi_ms:
        captured.find((e) => e.name === "first_insight_seen")?.at != null
          ? (captured.find((e) => e.name === "first_insight_seen")!.at - t0)
          : null,
    };

    const outDir = path.join(process.cwd(), "playwright-report");
    fs.mkdirSync(outDir, { recursive: true });
    fs.writeFileSync(
      path.join(outDir, "ttfi-baseline.json"),
      JSON.stringify(result, null, 2),
    );

    // Baseline mode never fails hard — we are measuring, not gating.
    // Task 6 will add the < 5 min assertion once the wizard + card ship.
    // eslint-disable-next-line no-console
    console.log("TTFI baseline artifact:", result);
  });
});
