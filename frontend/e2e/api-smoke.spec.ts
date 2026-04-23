/**
 * Real-Backend API Smoke Tests — release gate (issue #656).
 *
 * Exercises the FastAPI + PostgreSQL stack directly via Playwright's
 * ``request`` fixture (no Next.js server or browser required). Every
 * request reaches the real backend — no ``page.route()`` mocks.
 *
 * Auth: ``X-API-Key`` header (API_KEY env on the running FastAPI process).
 *   The API-key path uses ``DEFAULT_TENANT_ID`` from settings, which is
 *   seeded to ``1`` by migration 003.
 *
 * Entry point for CI: ``npx playwright test --config playwright.real-backend.config.ts``
 * (see ``.github/workflows/ci.yml`` job ``e2e-real-backend``).
 */

import { test, expect } from "@playwright/test";

const API_KEY = process.env.E2E_API_KEY ?? "ci-e2e-test-key-for-ci-only";
const API_URL =
  process.env.E2E_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

const authHeaders = { "X-API-Key": API_KEY };

// ─── Health ──────────────────────────────────────────────────────────────────

test("health endpoint returns 200 and db_status ok", async ({ request }) => {
  const res = await request.get(`${API_URL}/health`, { headers: authHeaders });
  expect(res.status()).toBe(200);
  const body = await res.json();
  // /health returns "healthy" or "degraded" (503 = "unhealthy", which would
  // have already failed the status assertion above).
  expect(body.status).toMatch(/^(healthy|degraded)$/);
  // Authenticated callers (X-API-Key header is injected globally via
  // extraHTTPHeaders in the config) get the full checks breakdown.
  expect(body.checks?.database?.status).toBe("ok");
});

// ─── Golden path: sample load → pipeline run ─────────────────────────────────

test.describe("golden path — load-sample to pipeline run", () => {
  /**
   * POST /api/v1/onboarding/load-sample
   *
   * Inserts 5 000 synthetic pharma rows into bronze.sales, creates a
   * pipeline_run record, and returns `rows_loaded`. This is the most
   * important single operation in the onboarding flow — if it fails, no
   * tenant can ever see data. Proving it succeeds against a real DB is
   * the core promise of this test suite.
   */
  test("load-sample inserts rows and returns pipeline_run_id", async ({
    request,
  }) => {
    const res = await request.post(
      `${API_URL}/api/v1/onboarding/load-sample`,
      { headers: authHeaders },
    );

    expect(
      res.status(),
      `load-sample returned ${res.status()}: ${await res.text()}`,
    ).toBe(200);

    const body = await res.json();
    expect(body.rows_loaded).toBeGreaterThan(0);
    expect(typeof body.pipeline_run_id).toBe("string");
    expect(body.pipeline_run_id.length).toBeGreaterThan(0);
    expect(typeof body.duration_seconds).toBe("number");
  });

  /**
   * GET /api/v1/pipeline/runs/latest
   *
   * Verifies that the pipeline_run record created by load-sample is
   * retrievable — proves DB read-path works after the write.
   */
  test("pipeline latest returns the run created by load-sample", async ({
    request,
  }) => {
    // Ensure sample is loaded first.
    const loadRes = await request.post(
      `${API_URL}/api/v1/onboarding/load-sample`,
      { headers: authHeaders },
    );
    expect(loadRes.status()).toBe(200);
    const { pipeline_run_id } = await loadRes.json();

    const latestRes = await request.get(`${API_URL}/api/v1/pipeline/runs/latest`, {
      headers: authHeaders,
    });
    expect(latestRes.status()).toBe(200);

    const latest = await latestRes.json();
    // The pipeline run must be queryable; its ID must match what load-sample returned.
    expect(latest.run_id ?? latest.id ?? latest.pipeline_run_id).toBe(
      pipeline_run_id,
    );
  });
});

// ─── Auth sanity ─────────────────────────────────────────────────────────────

test("missing auth returns 401 not 500", async ({ request }) => {
  // No X-API-Key header and no Bearer token → must get 401 (auth error),
  // not 500 (unhandled exception). Verifies the auth guard is active in
  // the CI backend even in dev mode when API_KEY is set.
  const res = await request.get(`${API_URL}/api/v1/pipeline/runs/latest`);
  // 401 = auth rejected cleanly; anything 5xx = backend crash (bad)
  expect(res.status()).toBeLessThan(500);
  expect(res.status()).toBe(401);
});
