{{
    config(
        materialized='table',
        schema='marts',
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE {{ this }} FORCE ROW LEVEL SECURITY",
            "DROP POLICY IF EXISTS owner_all ON {{ this }}",
            "CREATE POLICY owner_all ON {{ this }} FOR ALL TO datapulse USING (true) WITH CHECK (true)",
            "DROP POLICY IF EXISTS reader_tenant ON {{ this }}",
            "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)"
        ]
    )
}}

-- Monthly seasonality indices for forecasting
-- Grain: one row per (tenant_id, month) — 12 rows per tenant
-- Used by Holt-Winters to understand yearly seasonal patterns

WITH monthly_totals AS (
    SELECT
        tenant_id,
        month,
        MIN(month_name)                         AS month_name,
        ROUND(AVG(total_sales), 2)              AS avg_monthly_revenue,
        ROUND(AVG(transaction_count), 2)        AS avg_monthly_txn,
        ROUND(STDDEV_POP(total_sales), 2)       AS stddev_monthly_revenue,
        COUNT(DISTINCT year)::INT               AS years_of_data
    FROM {{ ref('agg_sales_monthly') }}
    GROUP BY tenant_id, month
),

overall AS (
    SELECT
        tenant_id,
        ROUND(AVG(total_sales), 2) AS grand_avg_revenue,
        ROUND(AVG(transaction_count), 2) AS grand_avg_txn
    FROM {{ ref('agg_sales_monthly') }}
    GROUP BY tenant_id
)

SELECT
    m.tenant_id,
    m.month,
    m.month_name,
    m.avg_monthly_revenue,
    m.avg_monthly_txn,
    m.stddev_monthly_revenue,
    m.years_of_data,
    -- Seasonal indices (1.0 = average month, >1 = above average)
    ROUND(m.avg_monthly_revenue / NULLIF(o.grand_avg_revenue, 0), 4) AS month_revenue_index,
    ROUND(m.avg_monthly_txn / NULLIF(o.grand_avg_txn, 0), 4)        AS month_txn_index
FROM monthly_totals m
INNER JOIN overall o ON m.tenant_id = o.tenant_id
ORDER BY m.tenant_id, m.month
