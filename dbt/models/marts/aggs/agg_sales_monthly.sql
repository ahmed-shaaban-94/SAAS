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

-- Monthly sales aggregation with MoM and YoY growth
-- Grain: one row per (tenant_id, year, month, site_key)

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
            SUM(f.net_amount) / NULLIF(COUNT(DISTINCT f.invoice_id), 0),
            2
        )                                                 AS avg_basket_size
    FROM {{ ref('fct_sales') }} f
    INNER JOIN {{ ref('dim_date') }} d ON f.date_key = d.date_key
    GROUP BY f.tenant_id, d.year, d.quarter, d.month, d.month_name, f.site_key
),

-- Build a date spine of all (year, month) combinations per tenant+site
-- so that LAG(1) always refers to the true previous calendar month,
-- even if that month had zero sales. Without this, LAG skips missing months.
month_spine AS (
    SELECT DISTINCT year, month
    FROM {{ ref('dim_date') }}
),

tenant_site_spine AS (
    SELECT DISTINCT tenant_id, site_key
    FROM monthly_base
),

full_spine AS (
    SELECT
        ts.tenant_id,
        ts.site_key,
        ms.year,
        ms.month
    FROM tenant_site_spine ts
    CROSS JOIN month_spine ms
),

monthly_filled AS (
    SELECT
        fs.tenant_id,
        fs.site_key,
        fs.year,
        fs.month,
        mb.quarter,
        mb.month_name,
        mb.total_quantity,
        mb.total_sales,
        mb.total_discount,
        mb.total_net_amount,
        mb.transaction_count,
        mb.return_count,
        mb.unique_customers,
        mb.unique_products,
        mb.unique_staff,
        mb.walk_in_count,
        mb.insurance_count,
        mb.avg_basket_size
    FROM full_spine fs
    LEFT JOIN monthly_base mb
        ON  fs.tenant_id = mb.tenant_id
        AND fs.site_key  = mb.site_key
        AND fs.year      = mb.year
        AND fs.month     = mb.month
),

with_growth AS (
    SELECT
        m.*,
        ROUND(
            m.return_count::NUMERIC / NULLIF(m.transaction_count, 0),
            4
        ) AS return_rate,
        LAG(m.total_net_amount, 1) OVER (
            PARTITION BY m.tenant_id, m.site_key ORDER BY m.year, m.month
        ) AS prev_month_net,
        LAG(m.total_net_amount, 12) OVER (
            PARTITION BY m.tenant_id, m.site_key ORDER BY m.year, m.month
        ) AS prev_year_net
    FROM monthly_filled m
)

SELECT
    g.*,
    ROUND(
        (g.total_net_amount - g.prev_month_net) / NULLIF(g.prev_month_net, 0),
        4
    ) AS mom_growth_pct,
    ROUND(
        (g.total_net_amount - g.prev_year_net) / NULLIF(g.prev_year_net, 0),
        4
    ) AS yoy_growth_pct
FROM with_growth g
