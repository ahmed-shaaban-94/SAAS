import { http, HttpResponse } from "msw";

const API = process.env.NEXT_PUBLIC_API_URL || "";

export const mockKPISummary = {
  today_gross: 125000,
  mtd_gross: 3500000,
  ytd_gross: 42000000,
  period_gross: 125000,
  period_transactions: 1250,
  period_customers: 850,
  today_discount: 5000,
  mom_growth_pct: 12.5,
  yoy_growth_pct: 8.3,
  daily_transactions: 1250,
  daily_customers: 850,
  avg_basket_size: 100,
  daily_returns: 15,
  mtd_transactions: 35000,
  ytd_transactions: 420000,
  sparkline: [
    { period: "2024-01-01", value: 100000 },
    { period: "2024-01-02", value: 110000 },
    { period: "2024-01-03", value: 125000 },
  ],
};

export const mockTrendResult = {
  points: [
    { period: "2024-01-01", value: 100000 },
    { period: "2024-01-02", value: 120000 },
    { period: "2024-01-03", value: 115000 },
  ],
  total: 335000,
  average: 111667,
  min: 100000,
  max: 120000,
  growth_pct: 15.0,
};

export const mockRankingResult = {
  items: [
    { rank: 1, key: 101, name: "Product A", value: 500000, pct_of_total: 35.2 },
    { rank: 2, key: 102, name: "Product B", value: 300000, pct_of_total: 21.1 },
    { rank: 3, key: 103, name: "Product C", value: 200000, pct_of_total: 14.1 },
  ],
  total: 1420000,
};

export const mockReturns = [
  {
    drug_name: "Drug X",
    drug_brand: "Brand X",
    customer_name: "Customer A",
    origin: "Pharma",
    return_quantity: 50,
    return_amount: 5000,
    return_count: 3,
    return_rate: 3.2,
  },
];

export const mockHealthy = { status: "healthy", database: "connected", timestamp: "2024-01-01T00:00:00Z" };
export const mockUnhealthy = { status: "unhealthy", database: "disconnected" };

export const mockPipelineRuns = {
  items: [
    {
      id: "run-uuid-1",
      tenant_id: 1,
      run_type: "full",
      status: "success",
      trigger_source: "webhook",
      started_at: "2024-01-01T10:00:00Z",
      finished_at: "2024-01-01T10:05:00Z",
      duration_seconds: 300,
      rows_loaded: 50000,
      error_message: null,
      metadata: {},
    },
    {
      id: "run-uuid-2",
      tenant_id: 1,
      run_type: "full",
      status: "failed",
      trigger_source: "manual",
      started_at: "2024-01-02T10:00:00Z",
      finished_at: "2024-01-02T10:01:00Z",
      duration_seconds: 60,
      rows_loaded: 0,
      error_message: "dbt timeout",
      metadata: {},
    },
  ],
  total: 2,
  offset: 0,
  limit: 50,
};

export const mockDashboardData = {
  kpi: mockKPISummary,
  daily_trend: mockTrendResult,
  monthly_trend: mockTrendResult,
  top_products: mockRankingResult,
  top_customers: mockRankingResult,
  top_staff: mockRankingResult,
  filter_options: { categories: ["Pharma"], brands: ["BrandA"], sites: [], staff: [] },
};

export const mockQualityScorecard = {
  runs: [
    {
      run_id: "run-1",
      run_type: "full",
      status: "success",
      started_at: "2024-01-01T10:00:00Z",
      total_checks: 10,
      passed: 9,
      failed: 1,
      warned: 0,
      pass_rate: 90.0,
    },
  ],
  overall_pass_rate: 90.0,
  total_runs: 1,
};

export const mockAuditLog = {
  items: [
    {
      id: 1,
      action: "api_call",
      endpoint: "/api/v1/analytics/summary",
      method: "GET",
      ip_address: "127.0.0.1",
      user_id: "user-1",
      response_status: 200,
      duration_ms: 45,
      created_at: "2024-01-01T10:00:00Z",
    },
  ],
  total: 1,
  page: 1,
  page_size: 50,
};

export const mockStaffQuota = [
  {
    staff_key: 1,
    staff_name: "Ahmed",
    staff_position: "Manager",
    year: 2024,
    month: 1,
    actual_revenue: 50000,
    actual_transactions: 100,
    target_revenue: 60000,
    target_transactions: 120,
    revenue_achievement_pct: 83.3,
    transactions_achievement_pct: 83.3,
    revenue_variance: -10000,
  },
];

export const mockLineageGraph = {
  nodes: [
    { name: "sales", layer: "bronze", model_type: "source" },
    { name: "stg_sales", layer: "silver", model_type: "view" },
  ],
  edges: [{ source: "sales", target: "stg_sales" }],
};

export const mockVouchers = [
  {
    id: 1,
    tenant_id: 1,
    code: "SUMMER25",
    discount_type: "percent",
    value: 25,
    max_uses: 10,
    uses: 2,
    status: "active",
    starts_at: null,
    ends_at: null,
    min_purchase: null,
    redeemed_txn_id: null,
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: 2,
    tenant_id: 1,
    code: "FLAT50",
    discount_type: "amount",
    value: 50,
    max_uses: 1,
    uses: 1,
    status: "redeemed",
    starts_at: null,
    ends_at: null,
    min_purchase: null,
    redeemed_txn_id: 1234,
    created_at: "2026-01-02T00:00:00Z",
  },
];

export const handlers = [
  http.get(`${API}/health`, () => HttpResponse.json(mockHealthy)),

  http.get(`${API}/api/v1/analytics/dashboard`, () => HttpResponse.json(mockDashboardData)),
  http.get(`${API}/api/v1/analytics/summary`, () => HttpResponse.json(mockKPISummary)),
  http.get(`${API}/api/v1/analytics/date-range`, () =>
    HttpResponse.json({ min_date: "2023-01-01", max_date: "2025-12-31" }),
  ),
  http.get(`${API}/api/v1/analytics/filters/options`, () =>
    HttpResponse.json({ categories: ["Pharma", "OTC"], brands: ["BrandA"], sites: [], staff: [] }),
  ),
  http.get(`${API}/api/v1/analytics/trends/daily`, () => HttpResponse.json(mockTrendResult)),
  http.get(`${API}/api/v1/analytics/trends/monthly`, () => HttpResponse.json(mockTrendResult)),
  http.get(`${API}/api/v1/analytics/products/top`, () => HttpResponse.json(mockRankingResult)),
  http.get(`${API}/api/v1/analytics/customers/top`, () => HttpResponse.json(mockRankingResult)),
  http.get(`${API}/api/v1/analytics/staff/top`, () => HttpResponse.json(mockRankingResult)),
  http.get(`${API}/api/v1/analytics/sites`, () => HttpResponse.json(mockRankingResult)),
  http.get(`${API}/api/v1/analytics/returns`, () => HttpResponse.json(mockReturns)),
  http.get(`${API}/api/v1/analytics/billing-breakdown`, () =>
    HttpResponse.json({ items: [], total: 0 }),
  ),
  http.get(`${API}/api/v1/analytics/customer-type-breakdown`, () =>
    HttpResponse.json({ items: [], total: 0 }),
  ),
  http.get(`${API}/api/v1/analytics/top-movers`, () =>
    HttpResponse.json({ gainers: [], losers: [], entity_type: "product" }),
  ),
  http.get(`${API}/api/v1/analytics/abc-analysis`, () =>
    HttpResponse.json({ items: [], entity_type: "product" }),
  ),
  http.get(`${API}/api/v1/analytics/heatmap`, () =>
    HttpResponse.json({ cells: [], year: 2024 }),
  ),
  http.get(`${API}/api/v1/analytics/returns/trend`, () =>
    HttpResponse.json({ points: [] }),
  ),
  http.get(`${API}/api/v1/analytics/segments/summary`, () => HttpResponse.json([])),

  http.get(`${API}/api/v1/pipeline/runs`, () => HttpResponse.json(mockPipelineRuns)),
  http.get(`${API}/api/v1/pipeline/runs/latest`, () =>
    HttpResponse.json(mockPipelineRuns.items[0]),
  ),
  http.post(`${API}/api/v1/pipeline/trigger`, () =>
    HttpResponse.json({ run_id: "new-run-uuid", status: "pending" }),
  ),

  http.get(`${API}/api/v1/forecasting/summary`, () =>
    HttpResponse.json({ forecasts: [] }),
  ),
  http.get(`${API}/api/v1/targets/summary`, () =>
    HttpResponse.json({ year: 2024, months: [] }),
  ),
  http.get(`${API}/api/v1/targets/alerts/log`, () => HttpResponse.json([])),

  http.get(`${API}/api/v1/ai-light/status`, () =>
    HttpResponse.json({ enabled: false, provider: null }),
  ),
  http.get(`${API}/api/v1/ai-light/summary`, () =>
    HttpResponse.json({ summary: "", generated_at: null }),
  ),
  http.get(`${API}/api/v1/ai-light/anomalies`, () =>
    HttpResponse.json({ anomalies: [], checked_at: null }),
  ),

  // New feature endpoints
  http.get(`${API}/api/v1/pipeline/quality/scorecard`, () =>
    HttpResponse.json(mockQualityScorecard),
  ),
  http.get(`${API}/api/v1/audit-log`, () => HttpResponse.json(mockAuditLog)),
  http.get(`${API}/api/v1/analytics/staff/quota`, () =>
    HttpResponse.json(mockStaffQuota),
  ),
  http.get(`${API}/api/v1/lineage/graph`, () =>
    HttpResponse.json(mockLineageGraph),
  ),
  http.get(`${API}/api/v1/lineage/graph/:model`, () =>
    HttpResponse.json(mockLineageGraph),
  ),
  http.get(`${API}/api/v1/analytics/products/:key/affinity`, () =>
    HttpResponse.json([]),
  ),
  http.get(`${API}/api/v1/analytics/customers/churn`, () =>
    HttpResponse.json([]),
  ),
  http.get(`${API}/api/v1/report-schedules`, () => HttpResponse.json([])),
  http.get(`${API}/api/v1/targets/summary/quarterly`, () =>
    HttpResponse.json({ year: 2024, quarters: [] }),
  ),

  // POS vouchers (Phase 1 discount engine)
  http.get(`${API}/api/v1/pos/vouchers`, ({ request }) => {
    const url = new URL(request.url);
    const status = url.searchParams.get("status");
    if (status) {
      return HttpResponse.json(mockVouchers.filter((v) => v.status === status));
    }
    return HttpResponse.json(mockVouchers);
  }),
  http.post(`${API}/api/v1/pos/vouchers/validate`, async ({ request }) => {
    const body = (await request.json()) as { code?: string; cart_subtotal?: number };
    const code = (body.code ?? "").toUpperCase();
    if (code === "SUMMER25") {
      return HttpResponse.json({
        code: "SUMMER25",
        discount_type: "percent",
        value: 25,
        remaining_uses: 8,
        expires_at: null,
        min_purchase: null,
      });
    }
    if (code === "FLAT50") {
      return HttpResponse.json({
        code: "FLAT50",
        discount_type: "amount",
        value: 50,
        remaining_uses: 1,
        expires_at: null,
        min_purchase: 200,
      });
    }
    if (code === "EXPIRED") {
      return HttpResponse.json({ detail: "voucher_expired" }, { status: 400 });
    }
    if (code === "SMALLCART") {
      return HttpResponse.json(
        { detail: "voucher_min_purchase_unmet" },
        { status: 400 },
      );
    }
    return HttpResponse.json({ detail: "voucher_not_found" }, { status: 404 });
  }),
  http.post(`${API}/api/v1/pos/vouchers`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json(
      {
        id: 99,
        tenant_id: 1,
        code: body.code,
        discount_type: body.discount_type,
        value: body.value,
        max_uses: body.max_uses ?? 1,
        uses: 0,
        status: "active",
        starts_at: body.starts_at ?? null,
        ends_at: body.ends_at ?? null,
        min_purchase: body.min_purchase ?? null,
        redeemed_txn_id: null,
        created_at: "2026-04-19T00:00:00Z",
      },
      { status: 201 },
    );
  }),
];
