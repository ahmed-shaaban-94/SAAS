-- Expression indexes for year*100+month filtering on aggregation tables.
-- These accelerate the most common analytics queries (rankings, ABC, top movers)
-- which filter by: WHERE year * 100 + month BETWEEN :start_ym AND :end_ym
-- Wrapped in schema check: public_marts is dbt-managed and may not exist in CI.

DO $$ BEGIN
IF EXISTS (
    SELECT 1 FROM information_schema.schemata
    WHERE schema_name = 'public_marts'
) THEN
    CREATE INDEX IF NOT EXISTS idx_agg_product_ym
        ON public_marts.agg_sales_by_product ((year * 100 + month));

    CREATE INDEX IF NOT EXISTS idx_agg_customer_ym
        ON public_marts.agg_sales_by_customer ((year * 100 + month));

    CREATE INDEX IF NOT EXISTS idx_agg_monthly_ym
        ON public_marts.agg_sales_monthly ((year * 100 + month));

    CREATE INDEX IF NOT EXISTS idx_agg_staff_ym
        ON public_marts.agg_sales_by_staff ((year * 100 + month));
ELSE
    RAISE NOTICE 'public_marts schema does not exist yet — skipping expression indexes';
END IF;
END $$;
