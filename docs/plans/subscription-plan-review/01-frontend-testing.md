# Track 1 — Frontend Testing

> **Status**: PLANNED
> **Priority**: CRITICAL
> **Current State**: 11 E2E test files, 0 unit/integration tests for 93 components and 20+ hooks

---

## Objective

Build a comprehensive frontend testing strategy with **unit tests** (Vitest + React Testing Library), **integration tests** (component interactions), and **hardened E2E tests** (Playwright) — achieving 70%+ component coverage and enabling E2E in CI.

---

## Why This Matters

- Backend has 97.3% coverage, frontend has ~5% — this asymmetry signals incomplete engineering
- No unit tests means refactoring is risky (no safety net)
- E2E tests disabled in CI = no regression protection
- Interviewers look for testing discipline as a senior engineer signal

---

## Scope

- Vitest + React Testing Library setup
- 40+ component unit tests
- 20+ hook tests
- Playwright E2E hardening (enable in CI)
- MSW (Mock Service Worker) for API mocking
- Coverage reporting integrated into CI

---

## Deliverables

| Deliverable | Description |
|-------------|-------------|
| Test infrastructure | Vitest config, RTL setup, MSW handlers, test utilities |
| Component unit tests | 40+ tests covering KPI cards, charts, tables, filters, error states |
| Hook tests | 20+ tests for all SWR hooks (mock fetch, loading/error states) |
| Integration tests | 10+ tests for page-level component interactions |
| E2E hardening | Fix flaky tests, add data-testid coverage, enable in CI |
| Coverage config | Vitest coverage reporter, minimum threshold enforcement |
| CI integration | GitHub Actions step for frontend tests + coverage gate |

---

## Technical Details

### Test Infrastructure Setup

```
frontend/
├── vitest.config.ts              # Vitest config with jsdom
├── src/
│   ├── __tests__/                # Unit + integration tests
│   │   ├── setup.ts              # RTL + MSW global setup
│   │   ├── mocks/
│   │   │   ├── handlers.ts       # MSW request handlers (all 10+ API endpoints)
│   │   │   └── server.ts         # MSW server instance
│   │   ├── components/
│   │   │   ├── kpi-card.test.tsx
│   │   │   ├── kpi-grid.test.tsx
│   │   │   ├── daily-trend-chart.test.tsx
│   │   │   ├── monthly-trend-chart.test.tsx
│   │   │   ├── ranking-table.test.tsx
│   │   │   ├── ranking-chart.test.tsx
│   │   │   ├── filter-bar.test.tsx
│   │   │   ├── sidebar.test.tsx
│   │   │   ├── health-indicator.test.tsx
│   │   │   ├── error-boundary.test.tsx
│   │   │   ├── empty-state.test.tsx
│   │   │   ├── loading-card.test.tsx
│   │   │   ├── product-overview.test.tsx
│   │   │   ├── customer-overview.test.tsx
│   │   │   ├── staff-overview.test.tsx
│   │   │   ├── site-overview.test.tsx
│   │   │   ├── returns-overview.test.tsx
│   │   │   └── ...40+ total
│   │   ├── hooks/
│   │   │   ├── use-summary.test.ts
│   │   │   ├── use-daily-trend.test.ts
│   │   │   ├── use-monthly-trend.test.ts
│   │   │   ├── use-top-products.test.ts
│   │   │   ├── use-top-customers.test.ts
│   │   │   ├── use-top-staff.test.ts
│   │   │   ├── use-sites.test.ts
│   │   │   ├── use-returns.test.ts
│   │   │   ├── use-health.test.ts
│   │   │   └── ...20+ total
│   │   └── pages/
│   │       ├── dashboard.test.tsx
│   │       ├── products.test.tsx
│   │       ├── customers.test.tsx
│   │       ├── staff.test.tsx
│   │       ├── sites.test.tsx
│   │       └── returns.test.tsx
```

### Testing Patterns

#### Component Unit Test Pattern
```tsx
// kpi-card.test.tsx
import { render, screen } from '@testing-library/react';
import { KpiCard } from '@/components/dashboard/kpi-card';

describe('KpiCard', () => {
  it('renders title and formatted value', () => {
    render(<KpiCard title="Revenue" value={1500000} format="currency" />);
    expect(screen.getByText('Revenue')).toBeInTheDocument();
    expect(screen.getByText('EGP 1,500,000')).toBeInTheDocument();
  });

  it('shows positive trend indicator for growth', () => {
    render(<KpiCard title="Revenue" value={100} trend={15.5} />);
    expect(screen.getByTestId('trend-up')).toBeInTheDocument();
  });

  it('shows negative trend indicator for decline', () => {
    render(<KpiCard title="Revenue" value={100} trend={-8.2} />);
    expect(screen.getByTestId('trend-down')).toBeInTheDocument();
  });

  it('handles null/undefined value gracefully', () => {
    render(<KpiCard title="Revenue" value={null} />);
    expect(screen.getByText('—')).toBeInTheDocument();
  });
});
```

#### Hook Test Pattern
```tsx
// use-summary.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { useSummary } from '@/hooks/use-summary';
import { SWRWrapper } from '../setup';

describe('useSummary', () => {
  it('fetches summary data with date filters', async () => {
    const { result } = renderHook(
      () => useSummary({ start_date: '2024-01-01', end_date: '2024-12-31' }),
      { wrapper: SWRWrapper }
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data?.total_revenue).toBeDefined();
  });

  it('returns error state on API failure', async () => {
    // MSW handler returns 500 for this test
    const { result } = renderHook(() => useSummary({}), { wrapper: SWRWrapper });
    await waitFor(() => expect(result.current.error).toBeDefined());
  });
});
```

#### MSW Handler Pattern
```ts
// handlers.ts
import { http, HttpResponse } from 'msw';

export const handlers = [
  http.get('*/api/v1/analytics/summary', () => {
    return HttpResponse.json({
      total_revenue: 15000000,
      total_quantity: 250000,
      total_transactions: 45000,
      avg_order_value: 333.33,
      unique_customers: 12000,
      unique_products: 8500,
      return_rate: 0.032,
    });
  }),
  // ... handlers for all endpoints
];
```

### E2E Hardening Checklist

| Issue | Fix |
|-------|-----|
| Flaky timeout failures | Increase to 30s, add `waitForLoadState('networkidle')` |
| Missing data-testid | Add to all interactive elements (buttons, inputs, cards) |
| CI environment | Docker-based Playwright with `--project=chromium` only |
| API dependency | MSW or fixture server for deterministic data |
| Screenshot artifacts | Upload on failure via GitHub Actions artifacts |

### Coverage Targets

| Layer | Target | Metric |
|-------|--------|--------|
| Component unit tests | 70% | Lines covered by Vitest |
| Hook tests | 90% | All hooks have happy + error path tests |
| E2E tests | 15 critical flows | User journeys tested end-to-end |
| Overall frontend | 60%+ | Combined Vitest coverage |

---

## Dependencies

- `vitest` + `@vitest/coverage-v8` (test runner + coverage)
- `@testing-library/react` + `@testing-library/jest-dom` (component testing)
- `msw` v2 (API mocking)
- Existing Playwright setup (E2E)

---

## Key Files (New)

| File | Purpose |
|------|---------|
| `frontend/vitest.config.ts` | Vitest configuration |
| `frontend/src/__tests__/setup.ts` | Global test setup (RTL + MSW) |
| `frontend/src/__tests__/mocks/handlers.ts` | MSW API mock handlers |
| `frontend/src/__tests__/components/*.test.tsx` | 40+ component tests |
| `frontend/src/__tests__/hooks/*.test.ts` | 20+ hook tests |
| `frontend/src/__tests__/pages/*.test.tsx` | 6 page integration tests |
