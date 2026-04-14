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
            "CREATE INDEX IF NOT EXISTS idx_feat_dispense_rate_product ON {{ this }} (tenant_id, product_key)",
            "CREATE INDEX IF NOT EXISTS idx_feat_dispense_rate_site ON {{ this }} (tenant_id, site_key)"
        ]
    )
}}

-- Dispense rate: average quantity dispensed per day per product per site
-- Uses last 90 days of agg_sales_daily for smoothing
-- Grain: one row per (tenant_id, product_key, site_key)

WITH daily AS (
    SELECT
        tenant_id,
        product_key,
        site_key,
        daily_quantity,
        date_key
    FROM {{ ref('agg_sales_daily') }}
    WHERE date_key >= (
        SELECT MAX(date_key) - 90
        FROM {{ ref('agg_sales_daily') }}
    )
),

rates AS (
    SELECT
        tenant_id,
        product_key,
        site_key,
        COUNT(*)                                                       AS active_days,
        SUM(daily_quantity)                                            AS total_dispensed_90d,
        ROUND(SUM(daily_quantity) / NULLIF(COUNT(*), 0), 4)           AS avg_daily_dispense,
        ROUND(SUM(daily_quantity) / NULLIF(COUNT(*) / 7.0, 0), 4)    AS avg_weekly_dispense,
        ROUND(SUM(daily_quantity) / NULLIF(COUNT(*) / 30.0, 0), 4)   AS avg_monthly_dispense,
        MAX(date_key)                                                  AS last_dispense_date_key
    FROM daily
    GROUP BY 1, 2, 3
)

SELECT
    r.tenant_id,
    r.product_key,
    r.site_key,
    r.active_days,
    r.total_dispensed_90d,
    r.avg_daily_dispense,
    r.avg_weekly_dispense,
    r.avg_monthly_dispense,
    r.last_dispense_date_key,
    p.drug_code,
    p.drug_name,
    p.drug_brand,
    s.site_code,
    s.site_name
FROM rates r
INNER JOIN {{ ref('dim_product') }} p
    ON r.product_key = p.product_key AND r.tenant_id = p.tenant_id
INNER JOIN {{ ref('dim_site') }} s
    ON r.site_key = s.site_key AND r.tenant_id = s.tenant_id
