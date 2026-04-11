-- Migration 031: Tenant-scoped composite indexes on aggregation tables
--
-- Context: Migration 023 added expression indexes on (year*100+month) alone.
-- In a multi-tenant system every query includes WHERE tenant_id = :tid, so
-- those indexes require a full-index scan filtered by tenant — inefficient.
--
-- These composite indexes put tenant_id first (equality predicate, most
-- selective) so the planner can skip to the tenant's slice immediately.
--
-- Rollback: DROP INDEX IF EXISTS <name>;
-- Wrapped in schema check: public_marts is dbt-managed and may not
-- exist in CI where dbt hasn't run yet.

DO $$ BEGIN
IF EXISTS (
    SELECT 1 FROM information_schema.schemata
    WHERE schema_name = 'public_marts'
) THEN
    -- agg_sales_by_product: top-product rankings + ABC analysis
    CREATE INDEX IF NOT EXISTS idx_agg_product_tenant_ym
        ON public_marts.agg_sales_by_product (tenant_id, (year * 100 + month));

    -- agg_sales_by_customer: customer ranking + churn detection
    CREATE INDEX IF NOT EXISTS idx_agg_customer_tenant_ym
        ON public_marts.agg_sales_by_customer (tenant_id, (year * 100 + month));

    -- agg_sales_by_staff: staff ranking + performance summary
    CREATE INDEX IF NOT EXISTS idx_agg_staff_tenant_ym
        ON public_marts.agg_sales_by_staff (tenant_id, (year * 100 + month));

    -- agg_sales_monthly: monthly trend + YoY comparison queries
    CREATE INDEX IF NOT EXISTS idx_agg_monthly_tenant_ym
        ON public_marts.agg_sales_monthly (tenant_id, (year * 100 + month));

    -- agg_sales_daily: date-range KPI queries (tenant + date_key range)
    CREATE INDEX IF NOT EXISTS idx_agg_daily_tenant_date
        ON public_marts.agg_sales_daily (tenant_id, date_key);

    -- metrics_summary: KPI snapshot lookups (tenant + exact date or range)
    CREATE INDEX IF NOT EXISTS idx_metrics_summary_tenant_date
        ON public_marts.metrics_summary (tenant_id, full_date);
ELSE
    RAISE NOTICE 'public_marts schema does not exist yet — skipping tenant composite indexes';
END IF;
END $$;
