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

-- Daily metrics summary with MTD and YTD running totals
-- Grain: one row per (tenant_id, day)
-- Note: unique_customers computed directly from fct_sales via COUNT(DISTINCT)
-- to avoid overcounting when summing pre-aggregated distinct counts from agg_sales_daily

WITH daily_from_fact AS (
    SELECT
        f.tenant_id,
        f.date_key,
        ROUND(SUM(f.net_amount), 2)              AS daily_net_amount,
        COUNT(*)::INT                             AS daily_transactions,
        COUNT(*) FILTER (WHERE f.is_return)::INT  AS daily_returns,
        COUNT(DISTINCT f.customer_key)::INT       AS daily_unique_customers
    FROM {{ ref('fct_sales') }} f
    GROUP BY f.tenant_id, f.date_key
),

daily_totals AS (
    SELECT
        dt.tenant_id,
        dt.date_key,
        d.full_date,
        d.year,
        d.month,
        dt.daily_net_amount,
        dt.daily_transactions,
        dt.daily_returns,
        dt.daily_unique_customers
    FROM daily_from_fact dt
    INNER JOIN {{ ref('dim_date') }} d ON dt.date_key = d.date_key
)

SELECT
    t.tenant_id,
    t.date_key,
    t.full_date,
    t.year,
    t.month,
    t.daily_net_amount,
    t.daily_transactions,
    t.daily_returns,
    t.daily_unique_customers,
    ROUND(
        SUM(t.daily_net_amount) OVER (
            PARTITION BY t.tenant_id, t.year, t.month
            ORDER BY t.full_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ),
        2
    ) AS mtd_net_amount,
    SUM(t.daily_transactions) OVER (
        PARTITION BY t.tenant_id, t.year, t.month
        ORDER BY t.full_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )::INT AS mtd_transactions,
    ROUND(
        SUM(t.daily_net_amount) OVER (
            PARTITION BY t.tenant_id, t.year
            ORDER BY t.full_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ),
        2
    ) AS ytd_net_amount,
    SUM(t.daily_transactions) OVER (
        PARTITION BY t.tenant_id, t.year
        ORDER BY t.full_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )::INT AS ytd_transactions
FROM daily_totals t
