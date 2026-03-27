{{
    config(
        materialized='table',
        schema='marts'
    )
}}

-- Monthly sales aggregation with MoM and YoY growth
-- Grain: one row per (year, month, site_key)

WITH monthly_base AS (
    SELECT
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
    GROUP BY d.year, d.quarter, d.month, d.month_name, f.site_key
),

with_growth AS (
    SELECT
        m.*,
        ROUND(
            m.return_count::NUMERIC / NULLIF(m.transaction_count, 0),
            4
        ) AS return_rate,
        LAG(m.total_net_amount, 1) OVER (
            PARTITION BY m.site_key ORDER BY m.year, m.month
        ) AS prev_month_net,
        LAG(m.total_net_amount, 12) OVER (
            PARTITION BY m.site_key ORDER BY m.year, m.month
        ) AS prev_year_net
    FROM monthly_base m
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
