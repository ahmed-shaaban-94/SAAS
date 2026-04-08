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
            "CREATE INDEX IF NOT EXISTS idx_feat_staff_quota_staff_key ON {{ this }} (tenant_id, staff_key)",
            "CREATE INDEX IF NOT EXISTS idx_feat_staff_quota_period ON {{ this }} (year, month)"
        ]
    )
}}

-- Staff quota attainment: actual sales vs targets
-- Grain: one row per (tenant_id, staff_key, year, month)
-- Joins agg_sales_by_staff with sales_targets (entity_type='staff')

WITH actuals AS (
    SELECT
        tenant_id,
        staff_key,
        year,
        month,
        staff_name,
        staff_position,
        total_net_amount AS actual_revenue,
        total_quantity AS actual_quantity,
        transaction_count AS actual_transactions
    FROM {{ ref('agg_sales_by_staff') }}
    WHERE staff_key > 0
),

targets AS (
    SELECT
        tenant_id,
        entity_key AS staff_key,
        EXTRACT(YEAR FROM period::date)::INT AS year,
        EXTRACT(MONTH FROM period::date)::INT AS month,
        target_type,
        target_value
    FROM public.sales_targets
    WHERE entity_type = 'staff'
      AND granularity = 'monthly'
),

targets_pivoted AS (
    SELECT
        tenant_id,
        staff_key,
        year,
        month,
        MAX(CASE WHEN target_type = 'revenue' THEN target_value END) AS target_revenue,
        MAX(CASE WHEN target_type = 'transactions' THEN target_value END) AS target_transactions
    FROM targets
    GROUP BY tenant_id, staff_key, year, month
)

SELECT
    a.tenant_id,
    a.staff_key,
    a.year,
    a.month,
    a.staff_name,
    a.staff_position,
    a.actual_revenue,
    a.actual_quantity,
    a.actual_transactions,
    t.target_revenue,
    t.target_transactions,
    CASE
        WHEN t.target_revenue IS NOT NULL AND t.target_revenue > 0
        THEN ROUND(a.actual_revenue / t.target_revenue * 100, 1)
    END AS revenue_achievement_pct,
    CASE
        WHEN t.target_transactions IS NOT NULL AND t.target_transactions > 0
        THEN ROUND(a.actual_transactions::NUMERIC / t.target_transactions * 100, 1)
    END AS transactions_achievement_pct,
    COALESCE(a.actual_revenue - t.target_revenue, 0) AS revenue_variance
FROM actuals a
LEFT JOIN targets_pivoted t
    ON a.tenant_id = t.tenant_id
    AND a.staff_key = t.staff_key
    AND a.year = t.year
    AND a.month = t.month
