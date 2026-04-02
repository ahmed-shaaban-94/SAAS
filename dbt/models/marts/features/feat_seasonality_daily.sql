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
            "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = (SELECT NULLIF(current_setting('app.tenant_id', true), '')::INT))"
        ]
    )
}}

-- Day-of-week seasonality indices for forecasting
-- Grain: one row per (tenant_id, day_of_week) — 7 rows per tenant
-- Egypt weekend: Friday (5) & Saturday (6)

WITH daily_with_dow AS (
    SELECT
        m.tenant_id,
        d.day_of_week,
        d.day_name,
        d.is_weekend,
        m.daily_net_amount,
        m.daily_transactions,
        m.daily_unique_customers
    FROM {{ ref('metrics_summary') }} m
    INNER JOIN {{ ref('dim_date') }} d ON m.date_key = d.date_key
),

dow_stats AS (
    SELECT
        tenant_id,
        day_of_week,
        MIN(day_name)                                  AS day_name,
        BOOL_OR(is_weekend)                            AS is_weekend,
        ROUND(AVG(daily_net_amount), 2)                AS avg_revenue_by_dow,
        ROUND(AVG(daily_transactions), 2)              AS avg_txn_by_dow,
        ROUND(AVG(daily_unique_customers), 2)          AS avg_customers_by_dow,
        ROUND(STDDEV_POP(daily_net_amount), 2)         AS stddev_revenue_by_dow,
        COUNT(*)::INT                                  AS sample_count
    FROM daily_with_dow
    GROUP BY tenant_id, day_of_week
),

overall AS (
    SELECT
        tenant_id,
        ROUND(AVG(daily_net_amount), 2)   AS grand_avg_revenue,
        ROUND(AVG(daily_transactions), 2) AS grand_avg_txn
    FROM daily_with_dow
    GROUP BY tenant_id
)

SELECT
    s.tenant_id,
    s.day_of_week,
    s.day_name,
    s.is_weekend,
    s.avg_revenue_by_dow,
    s.avg_txn_by_dow,
    s.avg_customers_by_dow,
    s.stddev_revenue_by_dow,
    s.sample_count,
    -- Seasonal indices (1.0 = average day, >1 = above average)
    ROUND(s.avg_revenue_by_dow / NULLIF(o.grand_avg_revenue, 0), 4) AS dow_revenue_index,
    ROUND(s.avg_txn_by_dow / NULLIF(o.grand_avg_txn, 0), 4)        AS dow_txn_index
FROM dow_stats s
INNER JOIN overall o ON s.tenant_id = o.tenant_id
ORDER BY s.tenant_id, s.day_of_week
