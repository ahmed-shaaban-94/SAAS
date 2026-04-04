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
            "CREATE INDEX IF NOT EXISTS idx_feat_revenue_site_rolling_lookup ON {{ this }} (tenant_id, date_key, site_key)"
        ]
    )
}}

-- Per-site rolling features with cross-site comparison
-- Grain: one row per (tenant_id, date_key, site_key) — daily per site
-- Provides: site-level MAs, site vs average ratio, revenue share

WITH site_daily AS (
    SELECT
        a.tenant_id,
        a.date_key,
        a.site_key,
        d.full_date,
        ROUND(SUM(a.total_sales), 2)        AS daily_gross_amount,
        SUM(a.transaction_count)::INT        AS daily_transactions
    FROM {{ ref('agg_sales_daily') }} a
    INNER JOIN {{ ref('dim_date') }} d ON a.date_key = d.date_key
    GROUP BY a.tenant_id, a.date_key, a.site_key, d.full_date
),

with_rolling AS (
    SELECT
        sd.*,
        ROUND(AVG(sd.daily_gross_amount) OVER w7, 2)  AS site_ma_7d,
        ROUND(AVG(sd.daily_gross_amount) OVER w30, 2) AS site_ma_30d,
        ROUND(SUM(sd.daily_gross_amount) OVER w30, 2) AS site_sum_30d
    FROM site_daily sd
    WINDOW
        w7  AS (PARTITION BY sd.tenant_id, sd.site_key ORDER BY sd.full_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW),
        w30 AS (PARTITION BY sd.tenant_id, sd.site_key ORDER BY sd.full_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW)
),

cross_site AS (
    SELECT
        tenant_id,
        date_key,
        ROUND(AVG(site_ma_30d), 2) AS avg_site_ma_30d,
        ROUND(SUM(site_sum_30d), 2) AS total_sum_30d
    FROM with_rolling
    GROUP BY tenant_id, date_key
)

SELECT
    r.tenant_id,
    r.date_key,
    r.site_key,
    r.full_date,
    r.daily_gross_amount,
    r.daily_transactions,
    r.site_ma_7d,
    r.site_ma_30d,
    r.site_sum_30d,
    -- Site vs cross-site average (>1 = outperforming average site)
    ROUND(r.site_ma_30d / NULLIF(cs.avg_site_ma_30d, 0), 4) AS site_vs_avg_ratio,
    -- Site revenue share of total
    ROUND(r.site_sum_30d / NULLIF(cs.total_sum_30d, 0), 4)  AS site_revenue_share
FROM with_rolling r
INNER JOIN cross_site cs ON r.tenant_id = cs.tenant_id AND r.date_key = cs.date_key
