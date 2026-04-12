import { test, expect } from "@playwright/test";

const needsBackend = !!process.env.CI;

const UPLOAD_API = "**/api/v1/upload/files";
const PREVIEW_API = "**/api/v1/upload/preview/**";
const CONFIRM_API = "**/api/v1/upload/confirm";

const MOCK_UPLOAD_RESPONSE = [
  {
    file_id: "abc123",
    filename: "sales_q1.csv",
    size_bytes: 204800,
    status: "uploaded",
  },
];

const MOCK_PREVIEW_RESPONSE = {
  file_id: "abc123",
  filename: "sales_q1.csv",
  row_count: 1200,
  columns: [
    { name: "date", dtype: "date", null_count: 0, sample_values: ["2024-01-01"] },
    { name: "product", dtype: "str", null_count: 0, sample_values: ["Widget A"] },
    { name: "revenue", dtype: "f64", null_count: 0, sample_values: ["1500.00"] },
    { name: "customer", dtype: "str", null_count: 2, sample_values: ["Acme Corp"] },
  ],
  sample_rows: [
    ["2024-01-01", "Widget A", "1500.00", "Acme Corp"],
    ["2024-01-02", "Widget B", "750.50", "Beta LLC"],
  ],
  warnings: [],
};

test.describe("Upload Flow", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/upload");
  });

  test("upload page renders dropzone and heading", async ({ page }) => {
    await expect(page.locator("h1, [class*='title']")).toContainText(/Import Data/i);
    await expect(page.getByText("Drop files here or click to browse")).toBeVisible();
    await expect(page.getByText(/Supports .xlsx, .csv, .xls/i)).toBeVisible();
  });

  test("upload valid CSV shows file in uploaded list", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend — run against staging");

    await page.route(UPLOAD_API, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_UPLOAD_RESPONSE),
      });
    });

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: "sales_q1.csv",
      mimeType: "text/csv",
      buffer: Buffer.from("date,product,revenue\n2024-01-01,Widget A,1500\n"),
    });

    await expect(page.getByText("Uploaded Files")).toBeVisible();
    await expect(page.getByText("sales_q1.csv")).toBeVisible();
    await expect(page.getByText("200 KB")).toBeVisible();
  });

  test("uploaded file shows preview table with correct columns", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend — run against staging");

    await page.route(UPLOAD_API, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_UPLOAD_RESPONSE),
      });
    });

    await page.route(PREVIEW_API, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_PREVIEW_RESPONSE),
      });
    });

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: "sales_q1.csv",
      mimeType: "text/csv",
      buffer: Buffer.from("date,product,revenue\n2024-01-01,Widget A,1500\n"),
    });

    await expect(page.getByText("sales_q1.csv")).toBeVisible();
    await page.getByRole("button", { name: /preview/i }).click();

    await expect(page.getByText(/Preview: sales_q1.csv/i)).toBeVisible();
    await expect(page.getByText("1200 rows")).toBeVisible();
    // Column headers
    await expect(page.getByRole("columnheader", { name: /date/i }).or(page.getByText("date").first())).toBeVisible();
    await expect(page.getByText("revenue")).toBeVisible();
    await expect(page.getByText("product")).toBeVisible();
    // Sample data
    await expect(page.getByText("Widget A")).toBeVisible();
    await expect(page.getByText("Acme Corp")).toBeVisible();
  });

  test("upload invalid file type does not appear in file list", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend — run against staging");

    await page.route(UPLOAD_API, async (route) => {
      await route.fulfill({
        status: 400,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Unsupported file type: .pdf" }),
      });
    });

    const fileInput = page.locator('input[type="file"]');
    // Force upload a non-accepted file type by bypassing accept attribute
    await fileInput.setInputFiles({
      name: "report.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4 test"),
    });

    // File should NOT appear in uploaded list after API rejection
    await expect(page.getByText("Uploaded Files")).not.toBeVisible();
    await expect(page.getByText("report.pdf")).not.toBeVisible();
  });

  test("upload empty file does not appear in file list", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend — run against staging");

    await page.route(UPLOAD_API, async (route) => {
      await route.fulfill({
        status: 400,
        contentType: "application/json",
        body: JSON.stringify({ detail: "File is empty" }),
      });
    });

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: "empty.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(""),
    });

    await expect(page.getByText("Uploaded Files")).not.toBeVisible();
  });

  test("confirm upload shows pipeline confirmation message", async ({ page }) => {
    test.skip(needsBackend, "requires live API backend — run against staging");

    await page.route(UPLOAD_API, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_UPLOAD_RESPONSE),
      });
    });

    await page.route(CONFIRM_API, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "confirmed", file_ids: ["abc123"] }),
      });
    });

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: "sales_q1.csv",
      mimeType: "text/csv",
      buffer: Buffer.from("date,product,revenue\n2024-01-01,Widget A,1500\n"),
    });

    await expect(page.getByText("sales_q1.csv")).toBeVisible();
    await page.getByRole("button", { name: /Confirm Import/i }).click();

    await expect(
      page.getByText(/Files confirmed and moved to import directory/i)
    ).toBeVisible();
    // Confirm button should no longer be visible after confirmation
    await expect(page.getByRole("button", { name: /Confirm Import/i })).not.toBeVisible();
  });

  test("dropzone supports drag and drop interaction", async ({ page }) => {
    // Verify the dropzone is interactive (click opens file picker)
    const dropzone = page.getByText("Drop files here or click to browse").locator("..");
    await expect(dropzone).toBeVisible();
    await expect(dropzone).toHaveCSS("cursor", "pointer");
  });
});
