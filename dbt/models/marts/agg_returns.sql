{{
    config(
        materialized='table',
        schema='marts'
    )
}}

-- Returns analysis aggregation
-- Grain: one row per (product_key, customer_key, year, month)
-- Only return transactions (is_return = TRUE)
-- Quantities and amounts stored as absolute values

WITH returns_monthly AS (
    SELECT
        f.product_key,
        f.customer_key,
        d.year,
        d.month,
        f.billing_way,

        -- Measures (absolute values for returns)
        ABS(ROUND(SUM(f.quantity)::NUMERIC, 2))         AS return_quantity,
        ABS(ROUND(SUM(f.net_amount)::NUMERIC, 2))       AS return_amount,
        COUNT(*)                                         AS return_count

    FROM {{ ref('fct_sales') }} f
    INNER JOIN {{ ref('dim_date') }} d ON f.date_key = d.date_key
    WHERE f.is_return = TRUE
    GROUP BY f.product_key, f.customer_key, d.year, d.month, f.billing_way
)

SELECT
    r.product_key,
    p.drug_name,
    r.customer_key,
    c.customer_name,
    r.year,
    r.month,
    r.billing_way,
    r.return_quantity,
    r.return_amount,
    r.return_count
FROM returns_monthly r
INNER JOIN {{ ref('dim_product') }}  p ON r.product_key  = p.product_key
INNER JOIN {{ ref('dim_customer') }} c ON r.customer_key = c.customer_key
