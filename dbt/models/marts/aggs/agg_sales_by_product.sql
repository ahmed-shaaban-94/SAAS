{{
    config(
        materialized='table',
        schema='marts'
    )
}}

-- Product sales aggregation with denormalized product attributes
-- Grain: one row per (product_key, year, month)

WITH product_monthly AS (
    SELECT
        f.product_key,
        d.year,
        d.month,
        d.month_name,
        SUM(f.quantity)::NUMERIC(18,4)                                          AS total_quantity,
        COALESCE(SUM(f.quantity) FILTER (WHERE f.is_return), 0)::NUMERIC(18,4)  AS return_quantity,
        ROUND(SUM(f.sales), 2)                                                  AS total_sales,
        ROUND(SUM(f.discount), 2)                                               AS total_discount,
        ROUND(SUM(f.net_amount), 2)                                             AS total_net_amount,
        COUNT(*)::INT                                                           AS transaction_count,
        COUNT(*) FILTER (WHERE f.is_return)::INT                                AS return_count,
        COUNT(DISTINCT f.customer_key)::INT                                     AS unique_customers,
        COUNT(DISTINCT f.site_key)::INT                                         AS unique_sites,
        ROUND(
            SUM(f.net_amount) / NULLIF(COUNT(DISTINCT f.invoice_id), 0),
            2
        )                                                                       AS avg_basket_size
    FROM {{ ref('fct_sales') }} f
    INNER JOIN {{ ref('dim_date') }} d ON f.date_key = d.date_key
    GROUP BY f.product_key, d.year, d.month, d.month_name
),

with_rate AS (
    SELECT
        pm.*,
        ROUND(
            pm.return_count::NUMERIC / NULLIF(pm.transaction_count, 0),
            4
        ) AS return_rate
    FROM product_monthly pm
)

SELECT
    r.product_key,
    p.drug_code,
    p.drug_name,
    p.drug_brand,
    p.drug_category,
    p.drug_division,
    r.year,
    r.month,
    r.month_name,
    r.total_quantity,
    r.return_quantity,
    r.total_sales,
    r.total_discount,
    r.total_net_amount,
    r.transaction_count,
    r.return_count,
    r.return_rate,
    r.unique_customers,
    r.unique_sites,
    r.avg_basket_size
FROM with_rate r
INNER JOIN {{ ref('dim_product') }} p ON r.product_key = p.product_key
