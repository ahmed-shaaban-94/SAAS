{{
    config(
        materialized='incremental',
        unique_key=['tenant_id', 'year', 'month', 'site_key'],
        incremental_strategy='merge',
        schema='marts',
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE {{ this }} FORCE ROW LEVEL SECURITY",
            "DROP POLICY IF EXISTS owner_all ON {{ this }}",
            "CREATE POLICY owner_all ON {{ this }} FOR ALL TO datapulse USING (true) WITH CHECK (true)",
            "DROP POLICY IF EXISTS reader_tenant ON {{ this }}",
            "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)",
            "CREATE INDEX IF NOT EXISTS idx_agg_sales_monthly_year_month ON {{ this }} (year, month)",
            "CREATE INDEX IF NOT EXISTS idx_agg_monthly_tenant_ym ON {{ this }} (tenant_id, (year * 100 + month))"
        ]
    )
}}

-- Monthly sales aggregation with MoM and YoY growth
-- Grain: one row per (year, month, site_key)

WITH monthly_base AS (
    SELECT
        f.tenant_id,
        d.year,
        d.quarter,
        d.month,
        d.month_name,
        f.site_key,
        SUM(f.quantity)::NUMERIC(18,4)                    AS total_quantity,
        ROUND(SUM(f.sales), 2)                            AS total_sales,
        ROUND(SUM(f.discount), 2)                         AS total_discount,
        ROUND(SUM(f.net_amount), 2)                       AS total_net_amount,
        COUNT(*)::INT                                     AS transaction_count,
        COUNT(*) FILTER (WHERE f.is_return)::INT          AS return_count,
        COUNT(DISTINCT f.customer_key)::INT               AS unique_customers,
        COUNT(DISTINCT f.product_key)::INT                AS unique_products,
        COUNT(DISTINCT f.staff_key)::INT                  AS unique_staff,
        COUNT(*) FILTER (WHERE f.is_walk_in)::INT         AS walk_in_count,
        COUNT(*) FILTER (WHERE f.has_insurance)::INT      AS insurance_count,
        ROUND(
            SUM(f.sales) / NULLIF(COUNT(DISTINCT f.invoice_id), 0),
            2
        )                                                 AS avg_basket_size
    FROM {{ ref('fct_sales') }} f
    INNER JOIN {{ ref('dim_date') }} d ON f.date_key = d.date_key
    {% if is_incremental() %}
    WHERE f.date_key >= (
        SELECT TO_CHAR(
            MAKE_DATE(MAX(year), MAX(month), 1) - INTERVAL '400 days',
            'YYYYMMDD'
        )::INT
        FROM {{ this }}
    )
    {% endif %}
    GROUP BY f.tenant_id, d.year, d.quarter, d.month, d.month_name, f.site_key
),

with_growth AS (
    SELECT
        m.*,
        ROUND(
            m.return_count::NUMERIC / NULLIF(m.transaction_count, 0),
            4
        ) AS return_rate,
        LAG(m.total_sales, 1) OVER (
            PARTITION BY m.tenant_id, m.site_key ORDER BY m.year, m.month
        ) AS prev_month_sales,
        LAG(m.total_sales, 12) OVER (
            PARTITION BY m.tenant_id, m.site_key ORDER BY m.year, m.month
        ) AS prev_year_sales
    FROM monthly_base m
)

SELECT
    g.tenant_id,
    g.year,
    g.quarter,
    g.month,
    g.month_name,
    g.site_key,
    g.total_quantity,
    g.total_sales,
    g.total_net_amount,
    g.total_discount,
    g.transaction_count,
    g.return_count,
    g.unique_customers,
    g.unique_products,
    g.unique_staff,
    g.walk_in_count,
    g.insurance_count,
    g.avg_basket_size,
    g.return_rate,
    ROUND(
        (g.total_sales - g.prev_month_sales) / NULLIF(g.prev_month_sales, 0),
        4
    ) AS mom_growth_pct,
    ROUND(
        (g.total_sales - g.prev_year_sales) / NULLIF(g.prev_year_sales, 0),
        4
    ) AS yoy_growth_pct
FROM with_growth g
