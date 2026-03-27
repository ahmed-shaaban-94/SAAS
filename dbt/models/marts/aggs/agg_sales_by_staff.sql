{{
    config(
        materialized='table',
        schema='marts'
    )
}}

-- Staff performance aggregation
-- Grain: one row per (staff_key, year, month)
-- Includes volume, revenue, diversity, returns, and avg transaction value

WITH staff_monthly AS (
    SELECT
        f.staff_key,
        d.year,
        d.month,

        -- Volume
        ROUND(SUM(f.quantity)::NUMERIC, 2)              AS total_quantity,
        ROUND(SUM(f.sales)::NUMERIC, 2)                 AS total_sales,
        ROUND(SUM(f.discount)::NUMERIC, 2)              AS total_discount,
        ROUND(SUM(f.net_amount)::NUMERIC, 2)            AS total_net_amount,
        COUNT(*)                                         AS transaction_count,

        -- Diversity
        COUNT(DISTINCT f.customer_key)                   AS unique_customers,
        COUNT(DISTINCT f.product_key)                    AS unique_products,

        -- Returns
        SUM(CASE WHEN f.is_return THEN 1 ELSE 0 END)    AS return_count,

        -- Avg transaction value
        ROUND(
            SUM(f.net_amount)::NUMERIC
            / NULLIF(COUNT(*), 0),
            2
        )                                                AS avg_transaction_value

    FROM {{ ref('fct_sales') }} f
    INNER JOIN {{ ref('dim_date') }} d ON f.date_key = d.date_key
    GROUP BY f.staff_key, d.year, d.month
)

SELECT
    s.staff_key,
    st.staff_id,
    st.staff_name,
    st.staff_position,
    s.year,
    s.month,
    s.total_quantity,
    s.total_sales,
    s.total_discount,
    s.total_net_amount,
    s.transaction_count,
    s.unique_customers,
    s.unique_products,
    s.return_count,
    s.avg_transaction_value
FROM staff_monthly s
INNER JOIN {{ ref('dim_staff') }} st ON s.staff_key = st.staff_key
