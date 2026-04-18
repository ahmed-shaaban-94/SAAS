/**
 * Golden-Path Real-Backend TTFI Spec (Follow-up 1b / #421).
 *
 * Measures Time-to-First-Insight (TTFI) against a live backend — NO page.route()
 * mocks. Every request reaches a real server so the numbers reflect true latency.
 *
 * Gate: RUN_TTFI_REAL=1  (skipped in normal CI to avoid flakiness from network)
 *
 * Auth: inject a NextAuth session cookie minted from the droplet's NEXTAUTH_SECRET.
 *   Option A — pre-mint externally and pass as PLAYWRIGHT_API_TOKEN (raw JWT string)
 *   Option B — pass PLAYWRIGHT_NEXTAUTH_SECRET; this spec mints the cookie itself
 *
 * Output: playwright-report/ttfi-real.json  (per-run event deltas, median, p95)
 *
 * See frontend/e2e/README.md §"Real-backend TTFI runbook" for setup instructions.
 */

import { test, expect, type Page, type Browser } from "@playwright/test";
import { encode } from "next-auth/jwt";
import * as fs from "node:fs";
import * as path from "node:path";

// ─── Guards ───────────────────────────────────────────────────────────────────

const RUN_REAL = process.env.RUN_TTFI_REAL === "1";

/** Hard upper bound kept consistent with the mocked golden-path gate. */
const TTFI_LIMIT_MS = 5 * 60 * 1000;

/** How many passes to record before writing the report. */
const PASS_COUNT = Number(process.env.TTFI_PASSES ?? "1");

// ─── Auth helpers ─────────────────────────────────────────────────────────────

/**
 * Returns a base URL and a valid NextAuth session-token cookie value.
 *
 * Priority:
 *  1. PLAYWRIGHT_API_TOKEN — caller has already minted the JWT externally.
 *  2. PLAYWRIGHT_NEXTAUTH_SECRET — we mint inline using next-auth/jwt.
 */
async function resolveAuth(): Promise<{ baseURL: string; sessionToken: string }> {
  const baseURL =
    process.env.PLAYWRIGHT_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:3000";

  if (process.env.PLAYWRIGHT_API_TOKEN) {
    return { baseURL, sessionToken: process.env.PLAYWRIGHT_API_TOKEN };
  }

  const secret = process.env.PLAYWRIGHT_NEXTAUTH_SECRET;
  if (!secret) {
    throw new Error(
      "Real-backend spec requires either PLAYWRIGHT_API_TOKEN or PLAYWRIGHT_NEXTAUTH_SECRET. " +
        "See frontend/e2e/README.md §'Real-backend TTFI runbook'.",
    );
  }

  const nowSec = Math.floor(Date.now() / 1000);
  const ttl = 60 * 60 * 2; // 2 hours — enough for a measurement session
  const tenantId = process.env.PLAYWRIGHT_TEST_TENANT_ID ?? "1";

  const sessionToken = await encode({
    token: {
      sub: "auth0|playwright-real-backend-001",
      name: "Playwright Real-Backend",
      email: "playwright-real@datapulse.io",
      picture: null,
      tenant_id: tenantId,
      roles: ["admin"],
      accessToken: "playwright-real-backend-token",
      refreshToken: "playwright-real-backend-refresh",
      expiresAt: nowSec + ttl,
      iat: nowSec,
      exp: nowSec + ttl,
    },
    secret,
    maxAge: ttl,
  });

  return { baseURL, sessionToken };
}

/**
 * Creates a browser context pre-loaded with the NextAuth session cookie so
 * all requests in that context are authenticated against the real backend.
 */
async function createAuthContext(browser: Browser, baseURL: string, sessionToken: string) {
  const url = new URL(baseURL);
  return browser.newContext({
    baseURL,
    // Inject the cookie directly — no globalSetup storage state needed.
    storageState: {
      cookies: [
        {
          name: "next-auth.session-token",
          value: sessionToken,
          domain: url.hostname,
          path: "/",
          httpOnly: true,
          secure: url.protocol === "https:",
          sameSite: "Lax",
          expires: Math.floor(Date.now() / 1000) + 7200,
        },
      ],
      origins: [],
    },
  });
}

// ─── TTFI observer ────────────────────────────────────────────────────────────

interface CapturedEvent {
  name: string;
  at: number; // epoch ms
}

/**
 * Subscribes to the `ttfi:event` window CustomEvent — the same always-on seam
 * used by the mocked golden-path spec. No page.route() involved.
 */
async function installTtfiObserver(page: Page): Promise<CapturedEvent[]> {
  const captured: CapturedEvent[] = [];

  await page.exposeFunction("__realTtfiRecord", (name: string) => {
    captured.push({ name, at: Date.now() });
  });

  await page.addInitScript(() => {
    window.addEventListener("ttfi:event", (e: Event) => {
      const detail = (e as CustomEvent).detail as { name?: string } | undefined;
      if (!detail?.name) return;
      (window as unknown as { __realTtfiRecord: (n: string) => void }).__realTtfiRecord(
        detail.name,
      );
    });
  });

  // Block PostHog to keep noise out of network logs. Real API calls still go through.
  await page.route(/posthog\.com/, (route) => route.fulfill({ status: 200, body: "{}" }));

  return captured;
}

// ─── Report helpers ───────────────────────────────────────────────────────────

interface PassResult {
  pass: number;
  run_at: string;
  events: { name: string; delta_ms: number }[];
  ttfi_ms: number | null;
  passed_gate: boolean;
}

function writeReport(passes: PassResult[]): void {
  const ttfiValues = passes.map((p) => p.ttfi_ms).filter((v): v is number => v !== null);
  ttfiValues.sort((a, b) => a - b);

  const median =
    ttfiValues.length > 0 ? ttfiValues[Math.floor(ttfiValues.length / 2)] : null;
  const p95 =
    ttfiValues.length > 0
      ? ttfiValues[Math.floor(ttfiValues.length * 0.95)]
      : null;

  const report = {
    generated_at: new Date().toISOString(),
    base_url: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000",
    pass_count: passes.length,
    ttfi_limit_ms: TTFI_LIMIT_MS,
    ttfi_median_ms: median,
    ttfi_p95_ms: p95,
    all_passed_gate: passes.every((p) => p.passed_gate),
    passes,
  };

  const outDir = path.join(process.cwd(), "playwright-report");
  fs.mkdirSync(outDir, { recursive: true });
  const outPath = path.join(outDir, "ttfi-real.json");
  fs.writeFileSync(outPath, JSON.stringify(report, null, 2));
  // eslint-disable-next-line no-console
  console.log(`\nTTFI real-backend report → ${outPath}`);
  // eslint-disable-next-line no-console
  console.log(`  median ${median} ms  p95 ${p95} ms  limit ${TTFI_LIMIT_MS} ms`);
}

// ─── Spec ─────────────────────────────────────────────────────────────────────

test.describe("Golden Path — real-backend TTFI measurement (no mocks)", () => {
  test.skip(!RUN_REAL, "Set RUN_TTFI_REAL=1 to execute this spec against a real backend");

  // Override playwright.config baseURL with the droplet URL if provided.
  test.use({
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000",
  });

  test(`TTFI × ${PASS_COUNT} pass(es) — upload_started → first_insight_seen`, async ({
    browser,
  }) => {
    const { baseURL, sessionToken } = await resolveAuth();
    const passes: PassResult[] = [];

    for (let pass = 1; pass <= PASS_COUNT; pass++) {
      // eslint-disable-next-line no-console
      console.log(`\n── Pass ${pass}/${PASS_COUNT} ──`);

      const context = await createAuthContext(browser, baseURL, sessionToken);
      const page = await context.newPage();
      const captured = await installTtfiObserver(page);
      const t0 = Date.now();

      try {
        // 1. Land on /upload — fires upload_started.
        await page.goto("/upload");
        await expect(
          page.getByRole("button", { name: /use sample pharma data/i }),
        ).toBeVisible({ timeout: 20000 });

        // 2. Click the sample CTA — fires upload_completed after the real endpoint
        //    resolves (POST /api/v1/onboarding/load-sample runs a 5k-row pipeline).
        await page.getByRole("button", { name: /use sample pharma data/i }).click();

        // 3. Wait for the dashboard redirect — the pipeline may take several seconds.
        await page.waitForURL(/\/dashboard\?first_upload=1/, { timeout: 90000 });

        // 4. Wait for the first-insight card title to appear — this fires first_insight_seen.
        //    Use a broad locator: the card renders any non-empty title from the server.
        const insightCard = page.locator("[data-testid='first-insight-card']");
        await expect(insightCard).toBeVisible({ timeout: 30000 });
        const cardTitle = insightCard.locator("[data-testid='insight-title']");
        await expect(cardTitle).not.toBeEmpty({ timeout: 10000 });

        // Let the event loop settle so the listener has recorded all events.
        await page.waitForTimeout(500);

        const uploadStarted = captured.find((e) => e.name === "upload_started");
        const insightSeen = captured.find((e) => e.name === "first_insight_seen");
        const ttfiMs =
          uploadStarted && insightSeen ? insightSeen.at - uploadStarted.at : null;
        const passedGate = ttfiMs !== null && ttfiMs < TTFI_LIMIT_MS;

        // eslint-disable-next-line no-console
        console.log(`  events: ${captured.map((e) => e.name).join(" → ")}`);
        // eslint-disable-next-line no-console
        console.log(`  TTFI: ${ttfiMs} ms (gate ${passedGate ? "✓" : "✗"})`);

        passes.push({
          pass,
          run_at: new Date(t0).toISOString(),
          events: captured.map((e) => ({ name: e.name, delta_ms: e.at - t0 })),
          ttfi_ms: ttfiMs,
          passed_gate: passedGate,
        });

        expect(
          ttfiMs,
          `Pass ${pass}: TTFI ${ttfiMs} ms ≥ limit ${TTFI_LIMIT_MS} ms`,
        ).toBeLessThan(TTFI_LIMIT_MS);
      } finally {
        await context.close();
      }
    }

    writeReport(passes);
  });
});
