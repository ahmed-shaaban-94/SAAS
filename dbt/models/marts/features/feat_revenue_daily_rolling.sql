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
            "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = (SELECT NULLIF(current_setting('app.tenant_id', true), '')::INT))",
            "CREATE INDEX IF NOT EXISTS idx_feat_revenue_daily_rolling_date_key ON {{ this }} (tenant_id, date_key)",
            "CREATE INDEX IF NOT EXISTS idx_feat_revenue_daily_rolling_full_date ON {{ this }} (tenant_id, full_date)"
        ]
    )
}}

-- Daily revenue rolling features for forecasting
-- Grain: one row per (tenant_id, date_key) — all sites combined
-- Provides: moving averages (7/30/90d), volatility, trend ratios, lag comparisons

WITH base_daily AS (
    SELECT
        m.tenant_id,
        m.date_key,
        d.full_date,
        d.day_of_week,
        d.is_weekend,
        d.month,
        d.year,
        d.year_month,
        m.daily_net_amount,
        m.daily_transactions,
        m.daily_unique_customers
    FROM {{ ref('metrics_summary') }} m
    INNER JOIN {{ ref('dim_date') }} d ON m.date_key = d.date_key
),

with_rolling AS (
    SELECT
        b.*,
        -- Revenue moving averages
        ROUND(AVG(b.daily_net_amount) OVER w7, 2)   AS ma_7d_revenue,
        ROUND(AVG(b.daily_net_amount) OVER w30, 2)  AS ma_30d_revenue,
        ROUND(AVG(b.daily_net_amount) OVER w90, 2)  AS ma_90d_revenue,
        -- Transaction moving averages
        ROUND(AVG(b.daily_transactions) OVER w7, 2)  AS ma_7d_txn,
        ROUND(AVG(b.daily_transactions) OVER w30, 2) AS ma_30d_txn,
        ROUND(AVG(b.daily_transactions) OVER w90, 2) AS ma_90d_txn,
        -- Volatility (30-day standard deviation)
        ROUND(STDDEV_POP(b.daily_net_amount) OVER w30, 2) AS volatility_30d,
        -- Rolling sums
        ROUND(SUM(b.daily_net_amount) OVER w7, 2)   AS sum_7d_revenue,
        ROUND(SUM(b.daily_net_amount) OVER w30, 2)  AS sum_30d_revenue
    FROM base_daily b
    WINDOW
        w7  AS (PARTITION BY b.tenant_id ORDER BY b.full_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW),
        w30 AS (PARTITION BY b.tenant_id ORDER BY b.full_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW),
        w90 AS (PARTITION BY b.tenant_id ORDER BY b.full_date ROWS BETWEEN 89 PRECEDING AND CURRENT ROW)
)

SELECT
    r.tenant_id,
    r.date_key,
    r.full_date,
    r.day_of_week,
    r.is_weekend,
    r.month,
    r.year,
    r.year_month,
    r.daily_net_amount,
    r.daily_transactions,
    r.daily_unique_customers,
    -- Moving averages
    r.ma_7d_revenue,
    r.ma_30d_revenue,
    r.ma_90d_revenue,
    r.ma_7d_txn,
    r.ma_30d_txn,
    r.ma_90d_txn,
    -- Volatility
    r.volatility_30d,
    -- Rolling sums
    r.sum_7d_revenue,
    r.sum_30d_revenue,
    -- Trend ratios (>1 = accelerating, <1 = decelerating)
    ROUND(r.ma_7d_revenue / NULLIF(r.ma_30d_revenue, 0), 4)  AS trend_ratio_7d_30d,
    ROUND(r.ma_30d_revenue / NULLIF(r.ma_90d_revenue, 0), 4) AS trend_ratio_30d_90d,
    -- Deviation from 30-day moving average
    ROUND(
        (r.daily_net_amount - r.ma_30d_revenue) / NULLIF(r.ma_30d_revenue, 0),
        4
    ) AS deviation_from_ma30,
    -- Lag comparisons
    LAG(r.daily_net_amount, 7) OVER (
        PARTITION BY r.tenant_id ORDER BY r.full_date
    ) AS same_day_last_week,
    LAG(r.daily_net_amount, 364) OVER (
        PARTITION BY r.tenant_id ORDER BY r.full_date
    ) AS same_day_last_year
FROM with_rolling r
