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
            "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)",
            "CREATE INDEX IF NOT EXISTS idx_feat_gamification_staff ON {{ this }} (tenant_id, staff_key)",
            "CREATE INDEX IF NOT EXISTS idx_feat_gamification_period ON {{ this }} (year, month)"
        ]
    )
}}

-- Gamification events: monthly metrics per staff for badge evaluation
-- Grain: one row per (tenant_id, staff_key, year, month)
-- Used by badge_rules engine to check badge eligibility

WITH monthly_staff AS (
    SELECT
        tenant_id,
        staff_key,
        year,
        month,
        staff_name,
        staff_position,
        total_net_amount AS monthly_revenue,
        total_quantity AS monthly_quantity,
        transaction_count AS monthly_txn_count,
        unique_customers AS monthly_customers,
        return_count AS monthly_returns
    FROM {{ ref('agg_sales_by_staff') }}
    WHERE staff_key > 0
),

-- Running total of all sales per staff (for first_sale badge)
cumulative AS (
    SELECT
        tenant_id,
        staff_key,
        year,
        month,
        SUM(monthly_txn_count) OVER (
            PARTITION BY tenant_id, staff_key
            ORDER BY year, month
            ROWS UNBOUNDED PRECEDING
        ) AS total_sales_count
    FROM monthly_staff
),

-- Month-over-month growth
growth AS (
    SELECT
        tenant_id,
        staff_key,
        year,
        month,
        monthly_revenue,
        LAG(monthly_revenue) OVER (
            PARTITION BY tenant_id, staff_key
            ORDER BY year, month
        ) AS prev_month_revenue,
        CASE
            WHEN LAG(monthly_revenue) OVER (
                PARTITION BY tenant_id, staff_key
                ORDER BY year, month
            ) > 0 THEN
                ROUND(
                    (monthly_revenue - LAG(monthly_revenue) OVER (
                        PARTITION BY tenant_id, staff_key
                        ORDER BY year, month
                    )) / LAG(monthly_revenue) OVER (
                        PARTITION BY tenant_id, staff_key
                        ORDER BY year, month
                    ) * 100,
                    1
                )
            ELSE 0
        END AS mom_growth_pct
    FROM monthly_staff
),

-- Consecutive months hitting 100% target (for perfect_quarter badge)
quota_streak AS (
    SELECT
        q.tenant_id,
        q.staff_key,
        q.year,
        q.month,
        q.revenue_achievement_pct,
        CASE WHEN q.revenue_achievement_pct >= 100 THEN 1 ELSE 0 END AS hit_target,
        SUM(CASE WHEN q.revenue_achievement_pct >= 100 THEN 1 ELSE 0 END) OVER (
            PARTITION BY q.tenant_id, q.staff_key
            ORDER BY q.year, q.month
            ROWS 2 PRECEDING
        ) AS consecutive_100pct_months
    FROM {{ ref('feat_staff_quota') }} q
    WHERE q.revenue_achievement_pct IS NOT NULL
)

SELECT
    ms.tenant_id,
    ms.staff_key,
    ms.year,
    ms.month,
    ms.staff_name,
    ms.staff_position,
    ms.monthly_revenue,
    ms.monthly_txn_count,
    ms.monthly_customers,
    ms.monthly_returns,
    ms.monthly_quantity,
    c.total_sales_count,
    COALESCE(g.mom_growth_pct, 0) AS mom_growth_pct,
    COALESCE(qs.consecutive_100pct_months, 0) AS consecutive_100pct_months,
    COALESCE(qs.revenue_achievement_pct, 0) AS revenue_achievement_pct
FROM monthly_staff ms
LEFT JOIN cumulative c
    ON ms.tenant_id = c.tenant_id
    AND ms.staff_key = c.staff_key
    AND ms.year = c.year
    AND ms.month = c.month
LEFT JOIN growth g
    ON ms.tenant_id = g.tenant_id
    AND ms.staff_key = g.staff_key
    AND ms.year = g.year
    AND ms.month = g.month
LEFT JOIN quota_streak qs
    ON ms.tenant_id = qs.tenant_id
    AND ms.staff_key = qs.staff_key
    AND ms.year = qs.year
    AND ms.month = qs.month
