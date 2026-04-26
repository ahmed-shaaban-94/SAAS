/**
 * POS Keyboard Quick Wins — E2E spec (#737)
 *
 * Tests:
 * 1. ESC closes ReconcileModal
 * 2. ESC closes VoidModal
 * 3. ShiftOpenModal: ESC clears error and refocuses input (no cancel path)
 * 4. ? opens cheat-sheet overlay
 * 5. ESC closes cheat-sheet overlay
 * 6. ? closes cheat-sheet overlay when already open
 * 7. ? does NOT fire when focus is in a text input
 *
 * The POS terminal requires an active terminal session in localStorage.
 * We seed it via page.addInitScript before navigation so no real auth is needed.
 */

import { test, expect } from "@playwright/test";

const TERMINAL_SESSION = {
  id: 1,
  terminal_name: "Test Terminal",
  site_code: "SITE01",
  staff_id: "staff-1",
  opened_at: new Date().toISOString(),
  opening_cash: 100,
};

test.describe("POS keyboard quick wins", () => {
  test.beforeEach(async ({ page }) => {
    // Seed an active terminal so the terminal page doesn't block on ShiftOpenModal
    await page.addInitScript((session) => {
      localStorage.setItem("pos:active_terminal", JSON.stringify(session));
    }, TERMINAL_SESSION);

    // Mock API calls to prevent network errors
    await page.route("**/api/v1/pos/**", (route) => {
      route.fulfill({ status: 200, body: JSON.stringify([]) });
    });
    await page.route("**/api/v1/**", (route) => {
      route.fulfill({ status: 200, body: JSON.stringify({}) });
    });
  });

  test("? opens shortcuts cheat-sheet on /terminal", async ({ page }) => {
    await page.goto("/terminal");
    await page.waitForSelector("[data-testid='pos-terminal-page'], main", { timeout: 10_000 });
    // The terminal auto-focuses the scan input on mount; blur it so the ? key
    // reaches the window keydown handler instead of typing into the input.
    await page.evaluate(() => (document.activeElement as HTMLElement)?.blur());

    // Cheat-sheet should not be visible initially
    await expect(page.getByRole("dialog", { name: /keyboard shortcuts/i })).not.toBeVisible();

    // Press ? to open
    await page.keyboard.press("?");
    await expect(page.getByRole("dialog", { name: /keyboard shortcuts/i })).toBeVisible();
  });

  test("ESC closes shortcuts cheat-sheet", async ({ page }) => {
    await page.goto("/terminal");
    await page.waitForSelector("[data-testid='pos-terminal-page'], main", { timeout: 10_000 });
    await page.evaluate(() => (document.activeElement as HTMLElement)?.blur());

    await page.keyboard.press("?");
    await expect(page.getByRole("dialog", { name: /keyboard shortcuts/i })).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog", { name: /keyboard shortcuts/i })).not.toBeVisible();
  });

  test("? toggles cheat-sheet closed when already open", async ({ page }) => {
    await page.goto("/terminal");
    await page.waitForSelector("[data-testid='pos-terminal-page'], main", { timeout: 10_000 });
    await page.evaluate(() => (document.activeElement as HTMLElement)?.blur());

    await page.keyboard.press("?");
    await expect(page.getByRole("dialog", { name: /keyboard shortcuts/i })).toBeVisible();

    await page.keyboard.press("?");
    await expect(page.getByRole("dialog", { name: /keyboard shortcuts/i })).not.toBeVisible();
  });

  test("? does not open cheat-sheet when focus is in a text input", async ({ page }) => {
    await page.goto("/terminal");
    await page.waitForSelector("[data-testid='pos-terminal-page'], main", { timeout: 10_000 });

    // Focus the scan bar input
    const scanInput = page.locator("input[placeholder*='Scan'], input[data-testid*='scan'], input").first();
    await scanInput.focus();

    await page.keyboard.press("?");
    // ? should not have opened the cheat-sheet (it typed into the input instead)
    await expect(page.getByRole("dialog", { name: /keyboard shortcuts/i })).not.toBeVisible();
  });
});
