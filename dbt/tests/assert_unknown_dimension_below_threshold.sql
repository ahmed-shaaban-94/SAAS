{{ config(tags=['quality_gate', 'marts']) }}

-- Data test: Verify that unknown dimension lookups (-1) in fct_sales
-- are below 5% for each dimension.
--
-- COALESCE(dim_key, -1) in fct_sales handles unmatched JOINs.
-- A high unknown rate (>5%) signals a data quality issue — either
-- the dimension is missing entries or JOIN keys are mismatched.
--
-- This test FAILS if any dimension has >5% unknown keys.

WITH dim_stats AS (
    SELECT
        COUNT(*) AS total_rows,
        COUNT(*) FILTER (WHERE product_key = -1) AS unknown_product,
        COUNT(*) FILTER (WHERE customer_key = -1) AS unknown_customer,
        COUNT(*) FILTER (WHERE site_key = -1) AS unknown_site,
        COUNT(*) FILTER (WHERE staff_key = -1) AS unknown_staff,
        COUNT(*) FILTER (WHERE billing_key = -1) AS unknown_billing
    FROM {{ ref('fct_sales') }}
),

pct AS (
    SELECT
        total_rows,
        ROUND(unknown_product * 100.0 / NULLIF(total_rows, 0), 2) AS product_unknown_pct,
        ROUND(unknown_customer * 100.0 / NULLIF(total_rows, 0), 2) AS customer_unknown_pct,
        ROUND(unknown_site * 100.0 / NULLIF(total_rows, 0), 2) AS site_unknown_pct,
        ROUND(unknown_staff * 100.0 / NULLIF(total_rows, 0), 2) AS staff_unknown_pct,
        ROUND(unknown_billing * 100.0 / NULLIF(total_rows, 0), 2) AS billing_unknown_pct
    FROM dim_stats
)

-- Return rows that violate the threshold (test fails if any rows returned)
SELECT *
FROM pct
WHERE product_unknown_pct > 5.0
   OR customer_unknown_pct > 5.0
   OR site_unknown_pct > 5.0
   OR staff_unknown_pct > 5.0
   OR billing_unknown_pct > 5.0
