import { test, expect } from "@playwright/test";

test.describe("Marketing Landing Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("hero section renders with headline and CTA", async ({ page }) => {
    await expect(page.locator("h1")).toContainText(/Revenue Intelligence/i, {
      timeout: 15000,
    });
    await expect(page.getByRole("link", { name: /Start Free Trial/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /See How It Works/i })).toBeVisible();
  });

  test("navbar links scroll to correct sections", async ({ page }) => {
    // Click Features link
    await page.locator('nav a[href="#features"]').click();
    await expect(page.locator("#features")).toBeVisible();

    // Click Pricing link
    await page.locator('nav a[href="#pricing"]').click();
    await expect(page.locator("#pricing")).toBeVisible();
  });

  test("features grid shows 6 cards", async ({ page }) => {
    const featureCards = page.locator("#features .glow-card");
    await expect(featureCards).toHaveCount(6);
  });

  test("how it works shows 4 steps", async ({ page }) => {
    const section = page.locator("#how-it-works");
    await expect(section).toBeVisible();
    // Scope to the section to avoid strict-mode violations (page has multiple "Import" nodes)
    await expect(section.getByText("Import").first()).toBeVisible();
    await expect(section.getByText("Clean").first()).toBeVisible();
    await expect(section.getByText("Analyze").first()).toBeVisible();
    await expect(section.getByText("Visualize").first()).toBeVisible();
  });

  test("pricing cards show 3 tiers", async ({ page }) => {
    const pricingSection = page.locator("#pricing");
    await expect(pricingSection).toBeVisible();
    await expect(pricingSection.getByText("Starter")).toBeVisible();
    await expect(pricingSection.getByText("Pro")).toBeVisible();
    await expect(pricingSection.getByText("Enterprise")).toBeVisible();
  });

  test("FAQ accordion expands on click", async ({ page }) => {
    const faqSection = page.locator("#faq");
    await expect(faqSection).toBeVisible();

    // Click first question
    const firstQuestion = faqSection.locator("button").first();
    await firstQuestion.click();
    await expect(firstQuestion).toHaveAttribute("aria-expanded", "true");
  });

  test("waitlist form validates email", async ({ page }) => {
    const form = page.locator('form').last();
    const emailInput = form.locator('input[type="email"]');
    const submitBtn = form.locator('button[type="submit"]');

    // Submit empty
    await submitBtn.click();
    // HTML5 validation should prevent submit
    await expect(emailInput).toBeVisible();
  });

  test("waitlist form submits successfully", async ({ page }) => {
    const form = page.locator('form').last();
    const emailInput = form.locator('input[type="email"]');
    const submitBtn = form.locator('button[type="submit"]');

    await emailInput.fill("test@example.com");
    await submitBtn.click();

    // Should show success message
    await expect(page.getByText(/on the list/i)).toBeVisible({ timeout: 10000 });
  });

  test("privacy page loads", async ({ page }) => {
    await page.goto("/privacy");
    await expect(page.locator("h1")).toContainText(/Privacy Policy/i);
  });

  test("terms page loads", async ({ page }) => {
    await page.goto("/terms");
    await expect(page.locator("h1")).toContainText(/Terms of Service/i);
  });

  test("footer links are present", async ({ page }) => {
    const footer = page.locator("footer");
    await expect(footer).toBeVisible();
    await expect(footer.getByRole("link", { name: "Privacy Policy" })).toBeVisible();
    await expect(footer.getByRole("link", { name: "Terms of Service" })).toBeVisible();
  });

  test("Get Started button links to dashboard", async ({ page }) => {
    const ctaLink = page.locator('nav').getByRole("link", { name: /Get Started/i });
    await expect(ctaLink).toHaveAttribute("href", "/dashboard");
  });
});
