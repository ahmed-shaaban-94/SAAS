{{
    config(
        materialized='table',
        schema='marts'
    )
}}

-- Customer sales aggregation with denormalized customer attributes
-- Grain: one row per (customer_key, year, month)

WITH customer_monthly AS (
    SELECT
        f.customer_key,
        d.year,
        d.month,
        d.month_name,
        SUM(f.quantity)::NUMERIC(18,4)                    AS total_quantity,
        ROUND(SUM(f.sales), 2)                            AS total_sales,
        ROUND(SUM(f.discount), 2)                         AS total_discount,
        ROUND(SUM(f.net_amount), 2)                       AS total_net_amount,
        COUNT(*)::INT                                     AS transaction_count,
        COUNT(*) FILTER (WHERE f.is_return)::INT          AS return_count,
        COUNT(DISTINCT f.product_key)::INT                AS unique_products,
        COUNT(*) FILTER (WHERE f.is_walk_in)::INT         AS walk_in_count,
        COUNT(*) FILTER (WHERE f.has_insurance)::INT      AS insurance_count,
        ROUND(
            SUM(f.net_amount) / NULLIF(COUNT(DISTINCT f.invoice_id), 0),
            2
        )                                                 AS avg_basket_size
    FROM {{ ref('fct_sales') }} f
    INNER JOIN {{ ref('dim_date') }} d ON f.date_key = d.date_key
    GROUP BY f.customer_key, d.year, d.month, d.month_name
)

SELECT
    cm.customer_key,
    c.customer_id,
    c.customer_name,
    cm.year,
    cm.month,
    cm.month_name,
    cm.total_quantity,
    cm.total_sales,
    cm.total_discount,
    cm.total_net_amount,
    cm.transaction_count,
    cm.return_count,
    cm.unique_products,
    cm.walk_in_count,
    cm.insurance_count,
    cm.avg_basket_size
FROM customer_monthly cm
INNER JOIN {{ ref('dim_customer') }} c ON cm.customer_key = c.customer_key
