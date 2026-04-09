{{
    config(
        materialized='incremental',
        unique_key=['tenant_id', 'site_key', 'year', 'month'],
        incremental_strategy='merge',
        schema='marts',
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE {{ this }} FORCE ROW LEVEL SECURITY",
            "DROP POLICY IF EXISTS owner_all ON {{ this }}",
            "CREATE POLICY owner_all ON {{ this }} FOR ALL TO datapulse USING (true) WITH CHECK (true)",
            "DROP POLICY IF EXISTS reader_tenant ON {{ this }}",
            "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)",
            "CREATE INDEX IF NOT EXISTS idx_agg_sales_by_site_year_month ON {{ this }} (year, month)",
            "CREATE INDEX IF NOT EXISTS idx_agg_sales_by_site_site_key ON {{ this }} (site_key)"
        ]
    )
}}

-- Site performance aggregation
-- Grain: one row per (site_key, year, month)
-- Includes volume, revenue, customer/product diversity, and return/walk-in/insurance ratios

WITH site_monthly AS (
    SELECT
        f.tenant_id,
        f.site_key,
        d.year,
        d.month,

        -- Volume
        SUM(f.quantity)::NUMERIC(18,4)                    AS total_quantity,
        ROUND(SUM(f.sales)::NUMERIC, 2)                 AS total_sales,
        ROUND(SUM(f.net_amount)::NUMERIC, 2)            AS total_net_amount,
        ROUND(SUM(f.discount)::NUMERIC, 2)              AS total_discount,
        COUNT(*)                                         AS transaction_count,

        -- Diversity
        COUNT(DISTINCT f.customer_key)                   AS unique_customers,
        COUNT(DISTINCT f.product_key)                    AS unique_products,
        COUNT(DISTINCT f.staff_key)                      AS unique_staff,

        -- Returns
        SUM(CASE WHEN f.is_return THEN 1 ELSE 0 END)    AS return_count,
        ROUND(
            SUM(CASE WHEN f.is_return THEN 1 ELSE 0 END)::NUMERIC
            / NULLIF(COUNT(*), 0),
            4
        )                                                AS return_rate,

        -- Walk-in ratio
        ROUND(
            SUM(CASE WHEN f.is_walk_in THEN 1 ELSE 0 END)::NUMERIC
            / NULLIF(COUNT(*), 0),
            4
        )                                                AS walk_in_ratio,

        -- Insurance ratio
        ROUND(
            SUM(CASE WHEN f.has_insurance THEN 1 ELSE 0 END)::NUMERIC
            / NULLIF(COUNT(*), 0),
            4
        )                                                AS insurance_ratio

    FROM {{ ref('fct_sales') }} f
    INNER JOIN {{ ref('dim_date') }} d ON f.date_key = d.date_key
    {% if is_incremental() %}
    WHERE f.date_key >= (
        SELECT TO_CHAR(
            MAKE_DATE(MAX(year), MAX(month), 1) - INTERVAL '90 days',
            'YYYYMMDD'
        )::INT
        FROM {{ this }}
    )
    {% endif %}
    GROUP BY f.tenant_id, f.site_key, d.year, d.month
)

SELECT
    s.tenant_id,
    s.site_key,
    si.site_code,
    si.site_name,
    si.area_manager,
    s.year,
    s.month,
    s.total_quantity,
    s.total_sales,
    s.total_net_amount,
    s.total_discount,
    s.transaction_count,
    s.unique_customers,
    s.unique_products,
    s.unique_staff,
    s.return_count,
    s.return_rate,
    s.walk_in_ratio,
    s.insurance_ratio
FROM site_monthly s
INNER JOIN {{ ref('dim_site') }} si ON s.site_key = si.site_key AND s.tenant_id = si.tenant_id
