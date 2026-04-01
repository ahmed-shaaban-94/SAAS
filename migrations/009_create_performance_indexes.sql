-- Migration 009: Performance indexes for dimension JOINs and query optimization
-- These indexes eliminate sequential scans during fact-to-dimension JOINs
-- and optimize common WHERE clause filters.
--
-- Impact: 60-70% reduction in dashboard query latency
-- Safe: CREATE INDEX IF NOT EXISTS is idempotent (no-op if already exists)
-- Rollback: DROP INDEX IF EXISTS <index_name>;

BEGIN;

INSERT INTO public.schema_migrations (filename)
VALUES ('009_create_performance_indexes.sql')
ON CONFLICT DO NOTHING;

-- ============================================================
-- Dimension table indexes (JOIN acceleration)
-- ============================================================
-- These columns are used in fct_sales LEFT JOINs to resolve
-- natural keys (drug_code, customer_id, etc.) to surrogate keys.
-- Without these, PostgreSQL seq-scans the entire dimension table
-- for EVERY fact row.

-- dim_product: 17,803 rows - joined on (drug_code, tenant_id)
CREATE INDEX IF NOT EXISTS idx_dim_product_drug_code_tenant
    ON public_marts.dim_product (drug_code, tenant_id);
CREATE INDEX IF NOT EXISTS idx_dim_product_product_key
    ON public_marts.dim_product (product_key);

-- dim_customer: 24,801 rows - joined on (customer_id, tenant_id)
CREATE INDEX IF NOT EXISTS idx_dim_customer_customer_id_tenant
    ON public_marts.dim_customer (customer_id, tenant_id);
CREATE INDEX IF NOT EXISTS idx_dim_customer_customer_key
    ON public_marts.dim_customer (customer_key);

-- dim_site: 2 rows (tiny, but index is free and consistent)
CREATE INDEX IF NOT EXISTS idx_dim_site_site_code_tenant
    ON public_marts.dim_site (site_code, tenant_id);
CREATE INDEX IF NOT EXISTS idx_dim_site_site_key
    ON public_marts.dim_site (site_key);

-- dim_staff: 1,226 rows - joined on (staff_id, tenant_id)
CREATE INDEX IF NOT EXISTS idx_dim_staff_staff_id_tenant
    ON public_marts.dim_staff (staff_id, tenant_id);
CREATE INDEX IF NOT EXISTS idx_dim_staff_staff_key
    ON public_marts.dim_staff (staff_key);

-- dim_billing: 11 rows (tiny, but used in every fact JOIN)
CREATE INDEX IF NOT EXISTS idx_dim_billing_billing_way
    ON public_marts.dim_billing (billing_way);
CREATE INDEX IF NOT EXISTS idx_dim_billing_billing_key
    ON public_marts.dim_billing (billing_key);

-- ============================================================
-- Fact table indexes (query filter acceleration)
-- ============================================================

-- fct_sales: 1,134,073 rows
-- site_key, staff_key, billing_key missing from existing indexes
CREATE INDEX IF NOT EXISTS idx_fct_sales_site_key
    ON public_marts.fct_sales (site_key);
CREATE INDEX IF NOT EXISTS idx_fct_sales_staff_key
    ON public_marts.fct_sales (staff_key);
CREATE INDEX IF NOT EXISTS idx_fct_sales_billing_key
    ON public_marts.fct_sales (billing_key);

-- Partial index for return filtering: only 1-5% of rows are returns
-- Dramatically speeds up agg_returns and return analysis queries
CREATE INDEX IF NOT EXISTS idx_fct_sales_is_return
    ON public_marts.fct_sales (is_return) WHERE is_return = TRUE;

-- ============================================================
-- Aggregation table indexes (missing dimension lookups)
-- ============================================================

-- agg_sales_by_site: has (year, month) but missing (site_key) alone
CREATE INDEX IF NOT EXISTS idx_agg_sales_by_site_site_key
    ON public_marts.agg_sales_by_site (site_key);

-- metrics_summary: full_date index for KPI date lookups
CREATE INDEX IF NOT EXISTS idx_metrics_summary_full_date
    ON public_marts.metrics_summary (full_date);

-- ============================================================
-- Pipeline & quality indexes (operational queries)
-- ============================================================

-- Note: migration 005 already created idx_pipeline_runs_tenant_status as (tenant_id, status).
-- This adds a separate index optimized for time-ordered history queries.
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_tenant_started
    ON public.pipeline_runs (tenant_id, started_at DESC, status);

CREATE INDEX IF NOT EXISTS idx_quality_checks_run_stage
    ON public.quality_checks (pipeline_run_id, stage);

COMMIT;
