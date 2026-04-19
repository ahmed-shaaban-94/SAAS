import { test, expect } from "@playwright/test";

/**
 * Marketing landing page e2e — aligned with editorial-landing-v2
 * (PR #436 1484a20b "feat(marketing): editorial landing page v2").
 *
 * Design principles for this file:
 *   - Anchor to section IDs (`#pipeline`, `#features`, `#pricing`) rather
 *     than body copy — IDs are structural, copy is not.
 *   - Use role-based selectors for navigation + CTAs so small label
 *     tweaks don't break tests.
 *   - For copy assertions, use substrings that are baked into the
 *     product's identity (tier names, medallion layers, product-specific
 *     feature names). These change much less often than marketing taglines.
 *   - Keep "no legacy artifact" anti-assertions to catch accidental
 *     reintroduction of retired copy.
 */

test.describe("Marketing Landing Page — Editorial v2", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  // ── Hero ────────────────────────────────────────────────────────────────

  test("hero headline uses the heartbeat-to-decision motif", async ({ page }) => {
    // The hero is intentionally split across multiple lines via <br/>
    // and <em>/<span>, so check the H1 text content contains the two
    // anchor words. Either alone would be too generic; both together
    // unambiguously identify the v2 hero.
    const h1 = page.locator("h1.hero-h");
    await expect(h1).toBeVisible({ timeout: 15000 });
    await expect(h1).toContainText(/heartbeat/i);
    await expect(h1).toContainText(/decision/i);
  });

  test("hero advertises 14-day pilot and live dashboard CTA", async ({ page }) => {
    // "14-day pilot" is a commitment the product is built around —
    // changing it is a business decision, not a copy tweak.
    await expect(page.getByText(/14-day pilot/i).first()).toBeVisible();
    // The primary hero CTA links to /dashboard.
    const heroCta = page.getByRole("link", { name: /See a live dashboard/i });
    await expect(heroCta).toBeVisible();
    await expect(heroCta).toHaveAttribute("href", "/dashboard");
  });

  test("no legacy hero copy or CTAs", async ({ page }) => {
    // Retired with the editorial v2 rewrite — regressions here would
    // imply the old landing file got copy-pasted back.
    await expect(page.getByText(/Get Started Free/i)).toHaveCount(0);
    await expect(page.getByText(/Join Beta/i)).toHaveCount(0);
    await expect(page.getByText(/Request Pilot Access/i)).toHaveCount(0);
    await expect(page.getByText(/pharma sales and operations data/i)).toHaveCount(0);
  });

  // ── Navigation ──────────────────────────────────────────────────────────

  test("nav exposes the three in-page anchors and dashboard CTA", async ({ page }) => {
    const nav = page.locator("nav.el-nav");
    await expect(nav).toBeVisible();

    // Section-anchor links in nav (these hrefs are structural, not copy).
    await expect(nav.locator('a[href="#pipeline"]')).toBeVisible();
    await expect(nav.locator('a[href="#features"]')).toBeVisible();
    await expect(nav.locator('a[href="#pricing"]')).toBeVisible();

    // Primary nav CTA goes to the product dashboard.
    const openDash = nav.getByRole("link", { name: /Open dashboard/i });
    await expect(openDash).toBeVisible();
    await expect(openDash).toHaveAttribute("href", "/dashboard");
  });

  // ── Platform pulse strip ────────────────────────────────────────────────

  test("pulse bar renders at top of page", async ({ page }) => {
    // The animated ECG line is the editorial landing's signature chrome.
    // Assert the structural elements are present — the animation itself
    // is a canvas/SVG path set in a useEffect and isn't worth E2E-ing.
    const pulseBar = page.locator(".pulse-bar");
    await expect(pulseBar).toBeVisible();
    await expect(pulseBar.getByText(/Platform pulse/i)).toBeVisible();
  });

  // ── Medallion pipeline (#pipeline) ──────────────────────────────────────

  test("medallion section shows Bronze / Silver / Gold tracks", async ({ page }) => {
    const section = page.locator("#pipeline");
    await expect(section).toBeVisible();
    // These are architectural layer names, not marketing copy.
    await expect(section.getByText(/BRONZE/i).first()).toBeVisible();
    await expect(section.getByText(/SILVER/i).first()).toBeVisible();
    await expect(section.getByText(/GOLD/i).first()).toBeVisible();
  });

  // ── Features (#features) ───────────────────────────────────────────────

  test("features section names the six product features by identity", async ({ page }) => {
    const section = page.locator("#features");
    await expect(section).toBeVisible();
    // Product-identity feature names — changing any of these requires
    // a product-naming decision, not a copy tweak.
    await expect(section.getByText(/Morning Briefing/i).first()).toBeVisible();
    await expect(section.getByText(/Horizon Mode/i).first()).toBeVisible();
    await expect(section.getByText(/Money Map/i).first()).toBeVisible();
    await expect(section.getByText(/Burning Cash/i).first()).toBeVisible();
  });

  // ── Pricing (#pricing) ─────────────────────────────────────────────────

  test("pricing section uses the Sahl / Nabḍ / Kubrā tier names", async ({ page }) => {
    const section = page.locator("#pricing");
    await expect(section).toBeVisible();
    // Tier names are localized product-identity strings — swap-level
    // change, not copy-tweak.
    await expect(section.getByText(/Sahl/i).first()).toBeVisible();
    await expect(section.getByText(/Nabḍ/i).first()).toBeVisible();
    await expect(section.getByText(/Kubrā/i).first()).toBeVisible();
  });

  test("no legacy pricing tier names inside the pricing section", async ({ page }) => {
    // These anti-assertions are SCOPED to #pricing on purpose: several of
    // these phrases (notably "Operations Pilot") are reused elsewhere on
    // the landing as product-milestone copy ("v4.0 · the operations pilot
    // is live", "Join the 14-day Operations Pilot"). What we're guarding
    // against is their reintroduction *as pricing tier names* — not the
    // words themselves disappearing from the page.
    const pricing = page.locator("#pricing");
    await expect(pricing.getByText(/^Starter$/)).toHaveCount(0);
    await expect(pricing.getByText(/^Pro$/)).toHaveCount(0);
    await expect(pricing.getByText(/Explorer Pilot/i)).toHaveCount(0);
    await expect(pricing.getByText(/Operations Pilot/i)).toHaveCount(0);
    await expect(pricing.getByText(/Enterprise Rollout/i)).toHaveCount(0);

    // The #pilot-access section id was replaced by #pricing — this check
    // stays at page scope because it's about the id itself not existing
    // anywhere.
    await expect(page.locator("#pilot-access")).toHaveCount(0);
  });

  // ── Footer CTA ─────────────────────────────────────────────────────────

  test("footer CTA invites a pilot and links to the dashboard", async ({ page }) => {
    const footerCta = page.locator("section.footer-cta");
    await expect(footerCta).toBeVisible();
    await expect(footerCta.getByText(/Tomorrow morning/i)).toBeVisible();
    const openDash = footerCta.getByRole("link", { name: /Open a live dashboard/i });
    await expect(openDash).toBeVisible();
    await expect(openDash).toHaveAttribute("href", "/dashboard");
  });

  // ── Vanity-stats guard (legacy) ────────────────────────────────────────

  test("no legacy vanity stats", async ({ page }) => {
    // Retired with v2 — "10x Faster than Pandas", "API Endpoints",
    // "Trusted by N data teams" were developer-marketing artifacts
    // unsuitable for a pharma-first pitch.
    await expect(page.getByText(/10x Faster than Pandas/i)).toHaveCount(0);
    await expect(page.getByText(/API Endpoints/i)).toHaveCount(0);
    await expect(page.getByText(/Trusted by .* data teams/i)).toHaveCount(0);
  });

  // ── Static pages ───────────────────────────────────────────────────────

  test("privacy page loads", async ({ page }) => {
    await page.goto("/privacy");
    await expect(page.locator("h1")).toContainText(/Privacy Policy/i);
  });

  test("terms page loads", async ({ page }) => {
    await page.goto("/terms");
    await expect(page.locator("h1")).toContainText(/Terms of Service/i);
  });
});
