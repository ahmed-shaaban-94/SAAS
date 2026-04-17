# Session 8: Integration Tests, E2E Tests, Polish

## Context Brief

**DataPulse** is a pharma SaaS. All 4 backend domains (inventory, expiry, purchase orders, dispensing) and all frontend pages have been built in Sessions 1-7.

> **Note**: POS integration is being designed in a separate session by another team member. This session focuses on integration tests, E2E tests, and polish.

**What already exists**:
- Session 1: Foundation (migrations 050-059, billing tiers, loader interface)
- Session 2: Inventory core (loaders, dbt models, API — 10 endpoints)
- Session 3: Expiry & batches (dim_batch, FEFO, API — 8 endpoints)
- Session 4: Purchase orders & suppliers (PO workflow, margins, API — 12 endpoints)
- Session 5: Dispensing analytics (derived features, API — 5 endpoints)
- Session 6: Frontend inventory + expiry pages
- Session 7: Frontend PO + dispensing + suppliers pages

**Goal**: Write cross-domain integration tests, Playwright E2E tests for all new pages, add empty states and error states, extend the upload route for inventory files, and verify the complete system works end-to-end.

---

## Task List

### 1. Cross-Domain Integration Tests

These tests verify that data flows correctly across domain boundaries.

#### `tests/test_integration_inventory_flow.py`
Test the complete inventory flow:
1. Create stock receipt (via loader or API adjustment)
2. Verify `fct_stock_movements` has a 'receipt' entry
3. Verify `agg_stock_levels` shows updated quantity
4. If stock drops below reorder_point, verify notification created
5. Create a stock adjustment (damage)
6. Verify stock level decreases accordingly

```python
"""Integration test: stock receipt -> movement -> stock level -> reorder alert."""

import pytest
from decimal import Decimal

class TestInventoryFlow:
    def test_receipt_creates_stock_movement(self, inventory_service, mock_repo):
        """Stock receipt should create a movement of type 'receipt'."""
        # Setup: create receipt
        # Assert: movement exists with type='receipt' and positive quantity

    def test_adjustment_reduces_stock(self, inventory_service, mock_repo):
        """Damage adjustment should reduce stock level."""
        # Setup: stock at 100, create damage adjustment for -10
        # Assert: stock level now 90

    def test_low_stock_triggers_reorder_alert(self, inventory_service, mock_repo, mock_notification_svc):
        """When stock drops below reorder_point, notification is created."""
        # Setup: reorder_point=50, current_stock=45
        # Assert: notification_svc.create_notification called with type_="stock_alert"

    def test_stock_valuation_after_receipts(self, inventory_service, mock_repo):
        """Weighted average cost updates after multiple receipts."""
        # Receipt 1: 100 units at $10 = $1000
        # Receipt 2: 50 units at $12 = $600
        # WAC = $1600 / 150 = $10.67
```

#### `tests/test_integration_po_receipt_flow.py`
Test PO -> receipt -> stock movement -> margin:
1. Create PO with 2 line items
2. Receive partial delivery (1 line)
3. Verify PO status = 'partial'
4. Verify stock_receipt created for received line
5. Verify margin analysis uses PO unit price as COGS
6. Receive remaining line
7. Verify PO status = 'received'

#### `tests/test_integration_expiry_flow.py`
Test batch -> near-expiry -> quarantine -> write-off:
1. Create batch with expiry_date = today + 20 days
2. Verify feat_expiry_alerts classifies as 'critical' (< 30 days)
3. Quarantine the batch
4. Verify batch status = 'quarantined'
5. Verify stock adjustment created (negative quantity)
6. Write off the batch
7. Verify batch status = 'written_off' with write_off_date

#### `tests/test_integration_dispensing_flow.py`
Test sales -> dispense rate -> days of stock -> stockout risk:
1. Given: agg_sales_daily shows 10 units/day for product X
2. Given: agg_stock_levels shows 50 units
3. Verify: feat_dispense_rate = 10/day
4. Verify: feat_days_of_stock = 5 days
5. Given: reorder_lead_days = 7
6. Verify: feat_stockout_risk = 'critical' (5 < 7)

---

### 2. Extend Upload Route for Inventory Files

**Modify `src/datapulse/api/routes/upload.py`** (or create new endpoints):

Add endpoints for uploading inventory Excel files:
- POST `/api/v1/upload/inventory-files` — accepts Excel files for stock_receipts, adjustments, counts, batches
- GET `/api/v1/upload/inventory-preview/{file_id}` — preview imported data before confirming
- POST `/api/v1/upload/inventory-confirm` — confirm and load data via the appropriate BronzeLoader

**Modify `src/datapulse/upload/service.py`**:
- Detect inventory file type from Excel headers (match against column maps)
- Use the loader registry to select the correct ExcelLoader
- Preview: read + validate without inserting
- Confirm: run the loader to insert to bronze

---

### 3. E2E Tests (Playwright)

All in `frontend/e2e/` directory. Follow existing patterns from `frontend/e2e/navigation.spec.ts`.

#### `frontend/e2e/inventory.spec.ts`
```typescript
import { test, expect } from "@playwright/test";

test.describe("Inventory Management", () => {
  test("navigates to inventory page", async ({ page }) => {
    await page.goto("/inventory");
    await expect(page).toHaveURL(/\/inventory/);
    await expect(page.getByRole("heading", { name: /Inventory/i })).toBeVisible();
  });

  test("displays stock level table", async ({ page }) => {
    await page.goto("/inventory");
    await expect(page.getByRole("table")).toBeVisible();
  });

  test("navigates to product detail", async ({ page }) => {
    await page.goto("/inventory");
    // Click first product row
    const firstRow = page.getByRole("row").nth(1);
    await firstRow.click();
    await expect(page).toHaveURL(/\/inventory\/.+/);
  });

  test("shows reorder alerts section", async ({ page }) => {
    await page.goto("/inventory");
    await expect(page.getByText(/Reorder Alerts/i)).toBeVisible();
  });
});
```

#### `frontend/e2e/expiry.spec.ts`
- Navigate to /expiry
- Verify calendar renders
- Verify near-expiry list has tabs (30d/60d/90d)
- Verify expired stock table renders

#### `frontend/e2e/purchase-orders.spec.ts`
- Navigate to /purchase-orders
- Verify PO list table renders
- Click "Create PO" button -> verify form opens
- Navigate to PO detail -> verify status pipeline

#### `frontend/e2e/dispensing.spec.ts`
- Navigate to /dispensing
- Verify dispense rate cards render
- Verify days-of-stock chart renders
- Verify velocity grid shows 4 sections

#### `frontend/e2e/suppliers.spec.ts`
- Navigate to /suppliers
- Verify supplier table renders
- Click supplier -> verify detail opens

---

### 4. Empty States and Error States

Create empty state components for when no data exists:

#### `frontend/src/components/inventory/empty-inventory.tsx`
```typescript
import { Package } from "lucide-react";

export function EmptyInventory() {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <Package className="h-12 w-12 text-muted-foreground mb-4" />
      <h3 className="text-lg font-semibold">No inventory data yet</h3>
      <p className="text-muted-foreground mt-2 max-w-sm">
        Upload stock receipt files or add inventory data manually to get started.
      </p>
    </div>
  );
}
```

Create similar empty states for:
- `frontend/src/components/expiry/empty-expiry.tsx` — "No batch data yet"
- `frontend/src/components/purchase-orders/empty-po.tsx` — "No purchase orders yet"

Update pages to show empty states when `data?.length === 0`.

---

### 5. Write Test for Upload Route

#### `tests/test_upload_inventory.py`
- Test file type detection (receipts vs adjustments vs counts)
- Test preview returns correct column mapping
- Test confirm triggers correct loader
- Test invalid file type returns 400

---

## Files Summary

| Action | Path |
|--------|------|
| CREATE | `tests/test_integration_inventory_flow.py` |
| CREATE | `tests/test_integration_po_receipt_flow.py` |
| CREATE | `tests/test_integration_expiry_flow.py` |
| CREATE | `tests/test_integration_dispensing_flow.py` |
| MODIFY | `src/datapulse/api/routes/upload.py` — add inventory file endpoints |
| MODIFY | `src/datapulse/upload/service.py` — add inventory file detection |
| CREATE | `tests/test_upload_inventory.py` |
| CREATE | `frontend/e2e/inventory.spec.ts` |
| CREATE | `frontend/e2e/expiry.spec.ts` |
| CREATE | `frontend/e2e/purchase-orders.spec.ts` |
| CREATE | `frontend/e2e/dispensing.spec.ts` |
| CREATE | `frontend/e2e/suppliers.spec.ts` |
| CREATE | `frontend/src/components/inventory/empty-inventory.tsx` |
| CREATE | `frontend/src/components/expiry/empty-expiry.tsx` |
| CREATE | `frontend/src/components/purchase-orders/empty-po.tsx` |

---

## Verification Commands

```bash
# Integration tests
pytest tests/test_integration_*.py -v

# Upload tests
pytest tests/test_upload_inventory.py -v

# Full Python regression
pytest tests/ -x --timeout=120 --cov=src/datapulse --cov-fail-under=95

# Frontend build
cd frontend && npm run build

# E2E tests
cd frontend && npx playwright test e2e/inventory.spec.ts e2e/expiry.spec.ts e2e/purchase-orders.spec.ts e2e/dispensing.spec.ts e2e/suppliers.spec.ts

# Lint
ruff format --check src/ tests/
ruff check src/ tests/
cd frontend && npx tsc --noEmit
```

## Exit Criteria

- [ ] All 4 integration tests pass — verifying cross-domain data flow
- [ ] Upload route correctly detects inventory file types from headers
- [ ] Upload preview returns data without inserting
- [ ] Upload confirm triggers correct loader
- [ ] All 5 E2E tests navigate to pages and verify key elements
- [ ] Empty states render when no data exists
- [ ] Full Python test suite passes with 95%+ coverage
- [ ] Frontend builds with zero errors
- [ ] Playwright tests pass
