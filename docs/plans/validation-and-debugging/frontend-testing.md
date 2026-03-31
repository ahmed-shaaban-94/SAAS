# Frontend Testing

Testing strategy for the Next.js 14 frontend: Playwright E2E tests and component testing.

## Current State (DONE)

- **E2E Framework**: Playwright (Chromium)
- **Test count**: 18+ specs across 6+ files
- **Config**: `frontend/playwright.config.ts`
- **Test directory**: `frontend/e2e/`

## Running Tests

```bash
# All E2E tests (Docker)
docker compose exec frontend npx playwright test

# All E2E tests (local)
cd frontend && npx playwright test

# Specific test file
npx playwright test e2e/dashboard.spec.ts

# With headed browser (local dev only)
npx playwright test --headed

# With UI mode (local dev only)
npx playwright test --ui

# Generate report
npx playwright test --reporter=html
npx playwright show-report
```

## Test Files

| File | Specs | Coverage Area |
|------|-------|---------------|
| `e2e/dashboard.spec.ts` | KPI cards, trend charts, filter bar | Executive overview page |
| `e2e/navigation.spec.ts` | Sidebar nav, active highlight, root redirect | App navigation |
| `e2e/filters.spec.ts` | Date preset clicks | Filter bar functionality |
| `e2e/pages.spec.ts` | All 5 analytics pages load | Page rendering |
| `e2e/health.spec.ts` | API health indicator | Health dot component |
| `e2e/pipeline.spec.ts` | Pipeline dashboard: title, trigger, overview, nav | Pipeline page |
| `e2e/website.spec.ts` | Public website: hero, features, pricing, FAQ, etc. | Marketing pages |

## Playwright Configuration

Key settings in `frontend/playwright.config.ts`:

```typescript
export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: { timeout: 5_000 },
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
```

## Test Patterns

### Page Load Test

```typescript
test('dashboard page loads', async ({ page }) => {
  await page.goto('/dashboard');
  await expect(page.getByRole('heading', { name: /overview/i })).toBeVisible();
});
```

### API-Dependent Test

```typescript
test('KPI cards display data', async ({ page }) => {
  await page.goto('/dashboard');
  // Wait for SWR to fetch and render
  await expect(page.getByTestId('kpi-grid')).toBeVisible();
  const cards = page.getByTestId('kpi-card');
  await expect(cards).toHaveCount(7);
});
```

### Interactive Test

```typescript
test('FAQ accordion expands on click', async ({ page }) => {
  await page.goto('/');
  const faqItem = page.getByRole('button', { name: /what is datapulse/i });
  await faqItem.click();
  await expect(page.getByText(/datapulse is a data analytics/i)).toBeVisible();
});
```

### Accessibility Test

```typescript
test('skip-to-content link works', async ({ page }) => {
  await page.goto('/');
  await page.keyboard.press('Tab');
  const skipLink = page.getByRole('link', { name: /skip to content/i });
  await expect(skipLink).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('#main-content')).toBeFocused();
});
```

## Test Data Strategy

- **API mocking**: Tests run against the real API (integration style). The API container must be running.
- **No mock service worker**: Tests validate the full stack from browser to database.
- **Stable selectors**: Use `data-testid`, `role`, and accessible names -- not CSS classes.

## Recommended Additions (TODO)

### Component Testing

Playwright supports component testing, or use Vitest + Testing Library:

```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom
```

Priority components for unit tests:

- [ ] `kpi-card.tsx` -- renders correct value, trend indicator, formatting
- [ ] `filter-bar.tsx` -- date presets update context
- [ ] `ranking-table.tsx` -- sorts data, handles empty state
- [ ] `formatters.ts` -- currency (EGP), percent, compact number formatting
- [ ] `date-utils.ts` -- `parseDateKey`, date presets
- [ ] `api-client.ts` -- `fetchAPI` error handling, Decimal parsing

### Visual Regression

- [ ] Add `@playwright/test` screenshot comparison for key pages
- [ ] Capture baseline screenshots for dashboard, products, landing page
- [ ] Compare on each PR to catch unintended visual changes

```typescript
test('dashboard visual regression', async ({ page }) => {
  await page.goto('/dashboard');
  await page.waitForLoadState('networkidle');
  await expect(page).toHaveScreenshot('dashboard.png', { maxDiffPixels: 100 });
});
```

### Mobile Testing

- [ ] Add a mobile viewport project to Playwright config

```typescript
projects: [
  { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  { name: 'mobile', use: { ...devices['iPhone 13'] } },
],
```

- [ ] Test sidebar drawer, mobile menu, responsive layouts

### Accessibility Automation

- [ ] Integrate `@axe-core/playwright` for automated a11y scanning

```typescript
import AxeBuilder from '@axe-core/playwright';

test('dashboard has no a11y violations', async ({ page }) => {
  await page.goto('/dashboard');
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});
```

### Test Coverage Goals

| Area | Current | Target |
|------|---------|--------|
| Page loads (all routes) | DONE | Maintain |
| KPI rendering | DONE | Maintain |
| Navigation | DONE | Maintain |
| Filters | DONE | Add date range picker |
| Theme toggle | DONE | Add visual regression |
| Public website | DONE | Maintain |
| Component units | None | 20+ specs |
| Mobile viewport | None | 10+ specs |
| Accessibility (axe) | None | All pages |

## Debugging Failed Tests

```bash
# Run with trace
npx playwright test --trace on

# View trace
npx playwright show-trace trace.zip

# Run with debug mode (pauses on failure)
PWDEBUG=1 npx playwright test

# Screenshot on failure (already in config via trace: 'on-first-retry')
# Check test-results/ directory after failures
```
