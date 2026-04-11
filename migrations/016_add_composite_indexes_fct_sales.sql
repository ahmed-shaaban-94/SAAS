-- 016: Add composite indexes on fct_sales for common query patterns
-- Idempotent: uses IF NOT EXISTS
-- Wrapped in schema check: public_marts is dbt-managed and may not
-- exist in CI where dbt hasn't run yet.

DO $$ BEGIN
IF EXISTS (
    SELECT 1 FROM information_schema.schemata
    WHERE schema_name = 'public_marts'
) THEN
    -- Accelerate product-filtered queries with tenant isolation
    CREATE INDEX IF NOT EXISTS idx_fct_sales_tenant_product
        ON public_marts.fct_sales (tenant_id, product_key);

    -- Accelerate customer-filtered queries with tenant isolation
    CREATE INDEX IF NOT EXISTS idx_fct_sales_tenant_customer
        ON public_marts.fct_sales (tenant_id, customer_key);

    -- Accelerate staff-filtered queries with tenant isolation
    CREATE INDEX IF NOT EXISTS idx_fct_sales_tenant_staff
        ON public_marts.fct_sales (tenant_id, staff_key);

    -- Accelerate date-range queries with tenant isolation
    CREATE INDEX IF NOT EXISTS idx_fct_sales_tenant_date
        ON public_marts.fct_sales (tenant_id, date_key);
ELSE
    RAISE NOTICE 'public_marts schema does not exist yet — skipping fct_sales indexes';
END IF;
END $$;
