# DataPulse — Frontend Engineer

## Your Role

You own the entire Next.js 14 frontend: all pages, components, SWR hooks, URL-driven filter state, Recharts visualizations, dark/light theming, and the API client. The frontend consumes the Analytics Engineer's endpoints and must stay in sync with backend Pydantic models. Performance, accessibility, and correct loading/error/empty states are your responsibility.

## Your Files

```
frontend/
├── Dockerfile                   # Multi-stage: dev + builder + production
├── tailwind.config.ts           # midnight-pharma color tokens + animations
├── src/
│   ├── app/
│   │   ├── layout.tsx           # Root layout: responsive sidebar + providers
│   │   ├── page.tsx             # Redirect to /dashboard
│   │   ├── not-found.tsx        # 404 page
│   │   ├── error.tsx            # Error boundary page
│   │   ├── dashboard/
│   │   │   ├── page.tsx         # Executive overview: KPI grid + trend charts
│   │   │   ├── loading.tsx      # Skeleton loading state
│   │   │   └── report/          # Print-optimized report page
│   │   ├── products/
│   │   ├── customers/
│   │   ├── staff/
│   │   ├── sites/
│   │   └── returns/
│   ├── components/
│   │   ├── layout/
│   │   │   ├── sidebar.tsx      # Nav sidebar (6 pages, responsive lg:flex)
│   │   │   ├── header.tsx
│   │   │   └── health-indicator.tsx
│   │   ├── dashboard/
│   │   │   ├── kpi-card.tsx     # KPI card: animated value, sparkline, trend pill
│   │   │   ├── kpi-grid.tsx     # 7 KPI cards grid
│   │   │   ├── daily-trend-chart.tsx   # Recharts AreaChart
│   │   │   └── monthly-trend-chart.tsx # Recharts BarChart
│   │   ├── filters/filter-bar.tsx     # Date preset filter bar + date range picker
│   │   ├── shared/
│   │   │   ├── ranking-table.tsx
│   │   │   ├── ranking-chart.tsx
│   │   │   ├── summary-stats.tsx
│   │   │   ├── chart-card.tsx
│   │   │   └── progress-bar.tsx
│   │   ├── products/product-overview.tsx
│   │   ├── customers/customer-overview.tsx
│   │   ├── staff/staff-overview.tsx
│   │   ├── sites/site-overview.tsx
│   │   ├── returns/returns-overview.tsx
│   │   ├── providers.tsx        # SWR + Filter context wrapper
│   │   ├── error-boundary.tsx   # React error boundary
│   │   ├── empty-state.tsx
│   │   └── loading-card.tsx
│   ├── hooks/                   # 9 SWR hooks (1 per API endpoint)
│   │   ├── use-summary.ts
│   │   ├── use-daily-trend.ts
│   │   ├── use-monthly-trend.ts
│   │   ├── use-top-products.ts
│   │   ├── use-top-customers.ts
│   │   ├── use-top-staff.ts
│   │   ├── use-sites.ts
│   │   ├── use-returns.ts
│   │   └── use-health.ts
│   ├── contexts/
│   │   └── filter-context.tsx   # Global filters synced to URL params
│   ├── types/
│   │   ├── api.ts               # TS interfaces matching Pydantic models
│   │   └── filters.ts           # FilterParams interface
│   └── lib/
│       ├── api-client.ts        # fetchAPI<T> + postAPI<T> + swrKey
│       ├── formatters.ts        # formatCurrency (EGP), formatPercent, formatCompact
│       ├── date-utils.ts        # parseDateKey, date presets
│       ├── constants.ts         # Chart colors, nav items, API_BASE_URL
│       └── utils.ts             # cn() helper
```

## Your Patterns

### SWR Hook

Every endpoint gets exactly one SWR hook. Use `swrKey()` for a stable, sorted cache key. Map filter params as needed before passing to the API.

```typescript
// frontend/src/hooks/use-summary.ts
import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { KPISummary } from "@/types/api";
import type { FilterParams } from "@/types/filters";

export function useSummary(filters?: FilterParams) {
  // /summary uses target_date, not start_date/end_date
  const targetDate = filters?.end_date;
  const params: FilterParams | undefined = targetDate ? { target_date: targetDate } : undefined;

  const key = swrKey("/api/v1/analytics/summary", params);
  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<KPISummary>("/api/v1/analytics/summary", params),
  );
  return { data, error, isLoading };
}
```

### URL-Driven Filter State

All filters live in URL search params — bookmarkable, shareable, no local state needed. Use `updateFilter()` for single or batch updates.

```typescript
// frontend/src/contexts/filter-context.tsx
export function FilterProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const filters = useMemo<FilterParams>(() => {
    const params: FilterParams = {};
    const startDate = searchParams.get("start_date");
    if (startDate) params.start_date = startDate;
    // ... other params
    return params;
  }, [searchParams]);

  const updateFilter = useCallback(
    (keyOrUpdates: keyof FilterParams | Partial<FilterParams>, value?: ...) => {
      const params = new URLSearchParams(searchParams.toString());
      if (typeof keyOrUpdates === "string") {
        value === undefined ? params.delete(keyOrUpdates) : params.set(keyOrUpdates, String(value));
      } else {
        Object.entries(keyOrUpdates).forEach(([k, v]) => {
          v === undefined ? params.delete(k) : params.set(k, String(v));
        });
      }
      router.push(`${pathname}?${params.toString()}`);
    },
    [searchParams, router, pathname],
  );
```

### Component Loading/Error/Empty Pattern

Every data-driven component must handle all three states. Use the shared primitives consistently.

```typescript
// Matches the pattern used in DailyTrendChart
export function DailyTrendChart() {
  const { data: dashboardData, error, isLoading } = useDashboardData();

  if (isLoading) return <LoadingCard lines={8} className="h-80" />;
  if (error) return <ErrorRetry title="Failed to load daily trend data"
                                description="Failed to load data. Please try again." />;
  if (!data || data.points.length === 0) return <EmptyState title="No daily trend data" />;

  return (
    <ChartCard title="Daily Revenue">
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={chartData}>...</AreaChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
```

### Chart Theme

Always use `useChartTheme()` for all Recharts color values. Never hardcode hex colors in chart components — they break in light mode.

```typescript
// frontend/src/hooks/use-chart-theme.ts (used by all chart components)
const CHART_THEME = useChartTheme();

<Area
  stroke={CHART_THEME.accent}
  fill={CHART_THEME.accent}
  fillOpacity={0.1}
/>
<CartesianGrid stroke={CHART_THEME.grid} />
<XAxis tick={{ fill: CHART_THEME.text }} />
```

### API Client

`fetchAPI<T>` handles: 15s timeout (AbortController), Bearer token from NextAuth session (fallback to localStorage), `parseDecimals()` to avoid JS float precision loss, `ApiError` with status code.

```typescript
// frontend/src/lib/api-client.ts
export async function fetchAPI<T>(path: string, params?: FilterParams): Promise<T> {
  const url = `${API_BASE_URL}${path}${buildQueryString(params)}`;
  return _request<T>(url);
}

export async function postAPI<T>(path: string, body?: unknown): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  return _request<T>(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
}
```

### Formatters

Use the shared formatters — never write inline formatting logic.

```typescript
import { formatCurrency, formatPercent, formatCompact, formatDuration } from "@/lib/formatters";

formatCurrency(1234567)  // "EGP 1,234,567"
formatPercent(12.3)      // "+12.3%"
formatCompact(1234567)   // "1.2M"
formatDuration(125)      // "2m 5s"
```

### KPI Card

The `KPICard` component handles animated count-up, sparkline (Recharts AreaChart), trend pill (green/red), and hover effects. Use `isCurrency` + `numericValue` for animated values.

```typescript
<KPICard
  label="MTD Revenue"
  value={formatCurrency(data.mtd_net)}
  numericValue={data.mtd_net}
  isCurrency
  trend={data.mom_growth_pct}
  trendLabel="vs last month"
  sparkline={data.sparkline}
  icon={TrendingUp}
/>
```

## Your Agents

- `/add-page <name>` — Scaffold Next.js page + loading.tsx + SWR hook + feature component + sidebar nav entry in `constants.ts`.
- `/add-chart <type> <name>` — Scaffold Recharts component with `useChartTheme()`, `ChartCard` wrapper, loading/error/empty states, and proper TypeScript types.

## Your Commands

```bash
# Dev server
cd frontend && npm run dev

# Type check (required before PR)
cd frontend && npx tsc --noEmit

# Lint
cd frontend && npm run lint

# Production build (catches build errors)
cd frontend && npm run build

# Run E2E tests
docker compose exec frontend npx playwright test

# Run single E2E spec
docker compose exec frontend npx playwright test e2e/dashboard.spec.ts

# Debug E2E (headed mode)
docker compose exec frontend npx playwright test --debug
```

## Your Rules

1. **Always handle three states: loading, error, empty.** Every component that fetches data must render `<LoadingCard />`, `<ErrorRetry />`, and `<EmptyState />`. Never render `null` on error.

2. **Always use `useChartTheme()`.** Never hardcode hex colors in Recharts components. `className="text-accent"` is allowed for Tailwind, but SVG `stroke` / `fill` props must use theme values.

3. **SWR key must include ALL filter params.** If a component depends on any filter, it must be in the key. Missing a param causes stale data bugs that are hard to reproduce.

4. **`"use client"` is required for components using hooks.** All components in `components/` that use `useState`, `useEffect`, `useContext`, or any custom hook need this directive at the top.

5. **Filters live in URL params, not state.** Use `useFilters()` from `filter-context.tsx`. Never use `useState` for filter values that should be bookmarkable or shareable.

6. **`types/api.ts` must match backend Pydantic models.** When the Analytics Engineer changes a model, sync `types/api.ts`. Field names must be identical (snake_case). Use `number` for `JsonDecimal` fields.

7. **Nav items belong in `lib/constants.ts`.** Don't hardcode nav items in `sidebar.tsx`. The `NAV_ITEMS` array is the single source of truth.

8. **Print styles go in `globals.css`.** Use `@media print` blocks in `globals.css` and `print:hidden` Tailwind class. Don't add print styles to individual components.

9. **Dynamic imports for below-fold components.** Anything not visible on initial render (heatmaps, detail modals, heavy charts) should use `next/dynamic` with `{ loading: () => <LoadingCard /> }`.

10. **`postAPI` for mutations, `fetchAPI` for reads.** Never use `fetchAPI` with a POST body. The SWR `mutate()` function should be called after successful mutations to refresh stale data.

---

## Project Overview

A data analytics platform for sales data: import raw Excel/CSV files, clean and transform through a medallion architecture (bronze/silver/gold), analyze with SQL, and visualize on interactive dashboards.

**Pipeline**: Import (Bronze) -> Clean (Silver) -> Analyze (Gold) -> Dashboard

## Architecture

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Database | PostgreSQL 16 (Docker) |
| Data Transform | dbt-core + dbt-postgres |
| Config | Pydantic Settings |
| ORM | SQLAlchemy 2.0 |
| Containers | Docker Compose |
| Frontend | Next.js 14 + TypeScript + Tailwind CSS |
| Charts | Recharts |
| Data Fetching | SWR |

## Docker Services

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| `api` | datapulse-api | 8000 | FastAPI analytics API |
| `frontend` | datapulse-frontend | 3000 | Next.js dashboard |
| `postgres` | datapulse-db | 5432 | PostgreSQL 16 |
| `redis` | datapulse-redis | (internal) | Redis cache |
| `n8n` | datapulse-n8n | 5678 | n8n workflow automation |
| `keycloak` | datapulse-keycloak | 8080 | Auth (OAuth2/OIDC) |

```bash
docker compose up -d --build
```

## Database (Gold Layer — API sources)

| Table/View | Rows | Purpose |
|-------|------|---------|
| `public_marts.agg_sales_daily` | 9,004 | Daily aggregation |
| `public_marts.agg_sales_monthly` | 36 | Monthly with MoM/YoY |
| `public_marts.agg_sales_by_product` | 161,703 | Product performance |
| `public_marts.agg_sales_by_customer` | 43,674 | Customer analytics |
| `public_marts.agg_sales_by_site` | 36 | Site performance |
| `public_marts.agg_sales_by_staff` | 3,123 | Staff performance |
| `public_marts.agg_returns` | 91,536 | Return analysis |
| `public_marts.metrics_summary` | 1,094 | Daily KPI with MTD/YTD |

## API Endpoints You Consume

| Endpoint | Hook | Data |
|----------|------|------|
| `GET /api/v1/analytics/summary` | `use-summary.ts` | KPI cards |
| `GET /api/v1/analytics/trends/daily` | `use-daily-trend.ts` | Area chart |
| `GET /api/v1/analytics/trends/monthly` | `use-monthly-trend.ts` | Bar chart |
| `GET /api/v1/analytics/products/top` | `use-top-products.ts` | Rankings |
| `GET /api/v1/analytics/customers/top` | `use-top-customers.ts` | Rankings |
| `GET /api/v1/analytics/staff/top` | `use-top-staff.ts` | Rankings |
| `GET /api/v1/analytics/sites` | `use-sites.ts` | Site cards |
| `GET /api/v1/analytics/returns` | `use-returns.ts` | Returns table |
| `GET /health` | `use-health.ts` | Health dot |

## Conventions

### Frontend Features
- **Theming**: Dark/light mode via `next-themes` (attribute="class", defaultTheme="dark"). CSS variables in `globals.css`, `useChartTheme` hook for Recharts SVG. Toggle in sidebar footer.
- **Date Range Picker**: `react-day-picker` + `@radix-ui/react-popover` in filter-bar alongside date presets.
- **Detail Page Trends**: Monthly revenue trend charts on product/customer/staff detail pages.
- **Print Report**: `/dashboard/report` page with `@media print` styles in `globals.css`.
- **Mobile**: Touch swipe-to-close on sidebar drawer (60px threshold).

### Security
- Authentication: NextAuth with Keycloak OIDC (`frontend/src/lib/auth.ts`)
- Route protection: `src/middleware.ts`
- API calls include `Authorization: Bearer <token>` from NextAuth session
- 15s fetch timeout (AbortController) on all API calls

### Testing
- Playwright E2E tests: 11 spec files in `frontend/e2e/`
- E2E selectors: prefer `data-testid` attributes; use generous timeouts for API-dependent elements
- Run: `docker compose exec frontend npx playwright test`

## Team Structure & Roles

| Role | Key Directories |
|------|----------------|
| **Pipeline Engineer** | `bronze/`, `pipeline/`, `dbt/`, `migrations/`, `n8n/` |
| **Analytics Engineer** | `analytics/`, `forecasting/`, `ai_light/`, `targets/`, `explore/` |
| **Platform Engineer** | `api/`, `core/`, `cache*.py`, `docker-compose*.yml` |
| **Frontend Engineer** | `frontend/src/` |
| **Quality & Growth Engineer** | `tests/`, `frontend/e2e/`, `android/`, `docs/` |

## Architecture Documentation

See `docs/ARCHITECTURE.md` for system diagrams, data flow, ERD, and deployment architecture.
