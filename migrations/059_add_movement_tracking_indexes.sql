-- Migration: 059 — Composite indexes for inventory movement query performance
-- Layer: Bronze
-- Idempotent.

-- Stock receipts: date-range queries by drug/site
CREATE INDEX IF NOT EXISTS idx_stock_receipts_drug_site_date
    ON bronze.stock_receipts(tenant_id, drug_code, site_code, receipt_date);

-- Stock adjustments: date-range queries by drug/site
CREATE INDEX IF NOT EXISTS idx_stock_adjustments_drug_site_date
    ON bronze.stock_adjustments(tenant_id, drug_code, site_code, adjustment_date);

-- Inventory counts: date-range queries by drug/site
CREATE INDEX IF NOT EXISTS idx_inventory_counts_drug_site_date
    ON bronze.inventory_counts(tenant_id, drug_code, site_code, count_date);
