{{ config(materialized='table', schema='marts') }}

-- Daily metrics summary with MTD and YTD running totals
-- Grain: one row per day (aggregated across all sites and billing ways)

WITH daily_totals AS (
    SELECT
        a.date_key,
        d.full_date,
        d.year,
        d.month,
        ROUND(SUM(a.total_net_amount), 2)       AS daily_net_amount,
        SUM(a.transaction_count)::INT            AS daily_transactions,
        SUM(a.return_count)::INT                 AS daily_returns,
        SUM(a.unique_customers)::INT             AS daily_unique_customers
    FROM {{ ref('agg_sales_daily') }} a
    INNER JOIN {{ ref('dim_date') }} d ON a.date_key = d.date_key
    GROUP BY a.date_key, d.full_date, d.year, d.month
)

SELECT
    t.date_key,
    t.full_date,
    t.year,
    t.month,
    t.daily_net_amount,
    t.daily_transactions,
    t.daily_returns,
    t.daily_unique_customers,
    ROUND(
        SUM(t.daily_net_amount) OVER (
            PARTITION BY t.year, t.month
            ORDER BY t.full_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ),
        2
    ) AS mtd_net_amount,
    SUM(t.daily_transactions) OVER (
        PARTITION BY t.year, t.month
        ORDER BY t.full_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )::INT AS mtd_transactions,
    ROUND(
        SUM(t.daily_net_amount) OVER (
            PARTITION BY t.year
            ORDER BY t.full_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ),
        2
    ) AS ytd_net_amount,
    SUM(t.daily_transactions) OVER (
        PARTITION BY t.year
        ORDER BY t.full_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )::INT AS ytd_transactions
FROM daily_totals t
