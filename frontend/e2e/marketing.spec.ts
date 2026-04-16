import { test, expect } from "@playwright/test";

test.describe("Marketing Landing Page — Pharma-First", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  // ── Hero ──────────────────────────────────────────────────────────────────

  test("hero headline is pharma-first", async ({ page }) => {
    await expect(page.locator("h1")).toContainText(
      "Turn pharma sales and operations data into daily decisions",
      { timeout: 15000 }
    );
  });

  test("primary CTA reads Request Pilot Access", async ({ page }) => {
    const ctas = page.getByRole("link", { name: /Request Pilot Access/i });
    await expect(ctas.first()).toBeVisible();
  });

  test("no generic Get Started or Join Beta CTAs exist", async ({ page }) => {
    await expect(page.getByText(/Get Started Free/i)).toHaveCount(0);
    await expect(page.getByText(/Join Beta/i)).toHaveCount(0);
    await expect(page.getByText(/Start Free Trial/i)).toHaveCount(0);
  });

  // ── Trust bar ─────────────────────────────────────────────────────────────

  test("no placeholder trust claims", async ({ page }) => {
    // Old: "Trusted by 500+ data teams worldwide"
    await expect(page.getByText(/Trusted by/i)).toHaveCount(0);
    // Old placeholder company names
    await expect(page.getByText("Pharma Corp")).toHaveCount(0);
    await expect(page.getByText("RetailMax")).toHaveCount(0);
  });

  test("trust bar shows pharma use-case list", async ({ page }) => {
    await expect(
      page.getByText(/branch performance/i)
    ).toBeVisible();
  });

  // ── Navigation ────────────────────────────────────────────────────────────

  test("navbar has Pilot Access link", async ({ page }) => {
    await expect(
      page.locator("nav").getByRole("link", { name: /Pilot Access/i }).first()
    ).toBeVisible();
  });

  test("navbar has See Demo secondary CTA", async ({ page }) => {
    await expect(
      page.locator("header").getByRole("link", { name: /See Demo/i })
    ).toBeVisible();
  });

  test("no Features nav link (renamed to Product or Use Cases)", async ({ page }) => {
    // Old nav had "Features" as a link — new nav has "Product" and "Use Cases"
    const featureNavLink = page.locator('nav a[href="#features"]');
    await expect(featureNavLink).toHaveCount(0);
  });

  // ── How It Works ──────────────────────────────────────────────────────────

  test("how it works shows pharma operational steps", async ({ page }) => {
    const section = page.locator("#how-it-works");
    await expect(section).toBeVisible();
    await expect(section.getByText(/Import your data/i).first()).toBeVisible();
    await expect(section.getByText(/Clean and validate/i).first()).toBeVisible();
    await expect(section.getByText(/See the business clearly/i).first()).toBeVisible();
    await expect(section.getByText(/Act faster/i).first()).toBeVisible();
  });

  // ── Features ──────────────────────────────────────────────────────────────

  test("features section shows pharma-specific capabilities", async ({ page }) => {
    const section = page.locator("#features");
    await expect(section).toBeVisible();
    await expect(section.getByText(/Inventory And Expiry/i).first()).toBeVisible();
  });

  // ── Stats ─────────────────────────────────────────────────────────────────

  test("no numeric vanity stats", async ({ page }) => {
    // Old: "2.2M+ Rows Processed", "10x Faster than Pandas", "25+ API Endpoints"
    await expect(page.getByText(/10x/i)).toHaveCount(0);
    await expect(page.getByText(/Faster than Pandas/i)).toHaveCount(0);
    await expect(page.getByText(/API Endpoints/i)).toHaveCount(0);
  });

  test("qualitative claims section is visible", async ({ page }) => {
    await expect(
      page.getByText(/Reporting cycles/i).first()
    ).toBeVisible();
  });

  // ── Pilot Access (formerly Pricing) ───────────────────────────────────────

  test("section is Pilot Access not Pricing", async ({ page }) => {
    await expect(page.locator("#pilot-access")).toBeVisible();
    await expect(page.locator("#pricing")).toHaveCount(0);
  });

  test("pilot tiers use correct names", async ({ page }) => {
    const section = page.locator("#pilot-access");
    await expect(section.getByText("Explorer Pilot")).toBeVisible();
    await expect(section.getByText("Operations Pilot")).toBeVisible();
    await expect(section.getByText("Enterprise Rollout")).toBeVisible();
  });

  test("no old pricing tier names", async ({ page }) => {
    await expect(page.getByText(/^Starter$/)).toHaveCount(0);
    await expect(page.getByText(/^Pro$/)).toHaveCount(0);
  });

  // ── FAQ ───────────────────────────────────────────────────────────────────

  test("FAQ has pharma-specific questions", async ({ page }) => {
    const faqSection = page.locator("#faq");
    await expect(faqSection).toBeVisible();
    await expect(
      faqSection.getByText(/Who is DataPulse for/i)
    ).toBeVisible();
  });

  test("no technical FAQ questions", async ({ page }) => {
    await expect(
      page.getByText(/What data formats does Data Pulse support/i)
    ).toHaveCount(0);
    await expect(
      page.getByText(/How does the medallion architecture work/i)
    ).toHaveCount(0);
  });

  // ── CTA Section ───────────────────────────────────────────────────────────

  test("bottom CTA section uses pharma-first copy", async ({ page }) => {
    await expect(
      page.getByText(/See what your team should act on every day/i)
    ).toBeVisible();
  });

  test("no waitlist or launch language in CTA", async ({ page }) => {
    await expect(page.getByText(/Join the waitlist/i)).toHaveCount(0);
    await expect(page.getByText(/Launch with clarity/i)).toHaveCount(0);
  });

  // ── Static pages ─────────────────────────────────────────────────────────

  test("privacy page loads", async ({ page }) => {
    await page.goto("/privacy");
    await expect(page.locator("h1")).toContainText(/Privacy Policy/i);
  });

  test("terms page loads", async ({ page }) => {
    await page.goto("/terms");
    await expect(page.locator("h1")).toContainText(/Terms of Service/i);
  });
});
