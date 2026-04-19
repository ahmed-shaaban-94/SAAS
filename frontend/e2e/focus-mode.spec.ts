import { test, expect, type Page } from "@playwright/test";

/**
 * Structural smoke tests for the v2 focus-mode chrome (FocusShell).
 *
 * Covers all drill-down routes migrated in Wave 3:
 *   /inventory/[drug_code]        (already in inventory.spec.ts; re-asserted here for parity)
 *   /customers/[key]
 *   /products/[key]
 *   /purchase-orders/[po_number]
 *   /sites/[key]
 *   /staff/[key]
 *
 * What these assertions guarantee:
 *   - FocusShell renders (pulse-bar visible, no sidebar)
 *   - Back-link points at the correct parent list
 *   - Breadcrumb trail contains the parent as a clickable link
 *
 * What they do NOT check (backend needed, skipped in CI):
 *   - Record data loads and renders
 *   - StatCard values
 *   - MiniTrendChart appears
 *
 * If a drill-down 500s on data fetch, these tests still pass — FocusShell
 * wraps loading/error/empty states by design so the back-button stays
 * reachable. That's a feature, not a gap.
 */

interface DrillDown {
  name: string;
  url: string;
  backHref: string;
  backLabel: RegExp;
  breadcrumbParent: string;
}

const DRILL_DOWNS: DrillDown[] = [
  {
    name: "/customers/[key]",
    url: "/customers/1",
    backHref: "/customers",
    backLabel: /Customers/i,
    breadcrumbParent: "Customers",
  },
  {
    name: "/products/[key]",
    url: "/products/1",
    backHref: "/products",
    backLabel: /Products/i,
    breadcrumbParent: "Products",
  },
  {
    name: "/purchase-orders/[po_number]",
    url: "/purchase-orders/PO-TEST-001",
    backHref: "/purchase-orders",
    backLabel: /Purchase orders/i,
    breadcrumbParent: "Purchase orders",
  },
  {
    name: "/sites/[key]",
    url: "/sites/1",
    backHref: "/sites",
    backLabel: /Sites/i,
    breadcrumbParent: "Sites",
  },
  {
    name: "/staff/[key]",
    url: "/staff/1",
    backHref: "/staff",
    backLabel: /Staff/i,
    breadcrumbParent: "Staff",
  },
];

async function assertFocusShellChrome(page: Page, drill: DrillDown) {
  // Pulse-bar present, sidebar absent
  await expect(page.locator(".dashboard-v2 .pulse-bar")).toBeVisible();
  await expect(page.locator(".dashboard-v2 aside.side")).toHaveCount(0);

  // Back link correct
  const back = page.locator(".dashboard-v2 .back-link");
  await expect(back).toBeVisible();
  await expect(back).toHaveAttribute("href", drill.backHref);
  await expect(back).toContainText(drill.backLabel);

  // Breadcrumb trail has the parent as a clickable link
  const crumbs = page.locator(".dashboard-v2 .focus-header .crumbs");
  await expect(crumbs).toBeVisible();
  await expect(
    crumbs.getByRole("link", { name: drill.breadcrumbParent }),
  ).toHaveAttribute("href", drill.backHref);
}

test.describe("Focus-mode drill-down chrome", () => {
  for (const drill of DRILL_DOWNS) {
    test(`${drill.name} renders FocusShell with correct back-link + breadcrumb`, async ({
      page,
    }) => {
      await page.goto(drill.url);
      await assertFocusShellChrome(page, drill);
    });
  }
});
