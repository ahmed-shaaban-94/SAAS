-- Expression indexes for year*100+month filtering on aggregation tables.
-- These accelerate the most common analytics queries (rankings, ABC, top movers)
-- which filter by: WHERE year * 100 + month BETWEEN :start_ym AND :end_ym

CREATE INDEX IF NOT EXISTS idx_agg_product_ym
    ON public_marts.agg_sales_by_product ((year * 100 + month));

CREATE INDEX IF NOT EXISTS idx_agg_customer_ym
    ON public_marts.agg_sales_by_customer ((year * 100 + month));

CREATE INDEX IF NOT EXISTS idx_agg_monthly_ym
    ON public_marts.agg_sales_monthly ((year * 100 + month));

CREATE INDEX IF NOT EXISTS idx_agg_staff_ym
    ON public_marts.agg_sales_by_staff ((year * 100 + month));
