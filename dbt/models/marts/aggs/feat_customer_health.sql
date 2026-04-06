{{
  config(
    materialized='table',
    schema='public_marts',
    tags=['analytics', 'customer_health']
  )
}}

/*
  Customer Health Score — composite 0-100 score per customer.

  Components (weighted):
    - Recency score  (30%): lower days since last purchase = higher
    - Frequency score (25%): higher 3-month frequency = higher
    - Monetary score  (25%): higher 3-month spend = higher
    - Return score   (10%): lower return rate = higher
    - Diversity score (10%): more unique products = higher

  Band thresholds:
    80-100 = Thriving, 60-79 = Healthy, 40-59 = Needs Attention,
    20-39 = At Risk, 0-19 = Critical
*/

WITH date_bounds AS (
    SELECT
        MAX(full_date) AS max_date,
        MAX(full_date) - INTERVAL '3 months' AS three_m_ago,
        MAX(full_date) - INTERVAL '6 months' AS six_m_ago,
        MAX(full_date) - INTERVAL '9 months' AS nine_m_ago
    FROM {{ ref('dim_date') }}
    WHERE full_date <= CURRENT_DATE
),

-- Current 3-month window
recent_activity AS (
    SELECT
        c.customer_key,
        c.customer_name,
        COUNT(DISTINCT f.date_key) AS frequency_3m,
        COALESCE(SUM(f.sales), 0) AS monetary_3m,
        COUNT(DISTINCT f.product_key) AS product_diversity,
        SUM(CASE WHEN f.is_return THEN 1 ELSE 0 END) AS return_count_3m,
        COUNT(*) AS total_txn_3m
    FROM {{ ref('fct_sales') }} f
    JOIN {{ ref('dim_customer') }} c ON f.customer_key = c.customer_key
    CROSS JOIN date_bounds db
    JOIN {{ ref('dim_date') }} d ON f.date_key = d.date_key
    WHERE d.full_date > db.three_m_ago
      AND c.customer_key > 0
    GROUP BY c.customer_key, c.customer_name
),

-- Previous 3-month window (for trend)
prior_activity AS (
    SELECT
        f.customer_key,
        COUNT(DISTINCT f.date_key) AS frequency_prev,
        COALESCE(SUM(f.sales), 0) AS monetary_prev
    FROM {{ ref('fct_sales') }} f
    CROSS JOIN date_bounds db
    JOIN {{ ref('dim_date') }} d ON f.date_key = d.date_key
    WHERE d.full_date > db.six_m_ago
      AND d.full_date <= db.three_m_ago
    GROUP BY f.customer_key
),

-- Recency: days since last transaction
recency AS (
    SELECT
        f.customer_key,
        (SELECT max_date FROM date_bounds) - MAX(d.full_date) AS recency_days
    FROM {{ ref('fct_sales') }} f
    JOIN {{ ref('dim_date') }} d ON f.date_key = d.date_key
    WHERE f.customer_key > 0
    GROUP BY f.customer_key
),

-- Percentile boundaries for normalization
percentiles AS (
    SELECT
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY r.recency_days) AS recency_p95,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY ra.frequency_3m) AS freq_p95,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY ra.monetary_3m) AS monetary_p95,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY ra.product_diversity) AS diversity_p95
    FROM recent_activity ra
    JOIN recency r ON ra.customer_key = r.customer_key
),

scored AS (
    SELECT
        ra.customer_key,
        ra.customer_name,
        COALESCE(r.recency_days, 999)::INT AS recency_days,
        ra.frequency_3m,
        ra.monetary_3m,
        ra.product_diversity,
        ROUND(
            CASE WHEN ra.total_txn_3m > 0
                THEN ra.return_count_3m::NUMERIC / ra.total_txn_3m
                ELSE 0
            END, 4
        ) AS return_rate,

        -- Normalize each component to 0-100
        -- Recency: inverted (lower days = better)
        GREATEST(0, LEAST(100,
            ROUND((1.0 - LEAST(COALESCE(r.recency_days, 999)::NUMERIC / NULLIF(p.recency_p95, 0), 1.0)) * 100, 2)
        )) AS recency_score,

        -- Frequency: higher = better
        GREATEST(0, LEAST(100,
            ROUND(LEAST(ra.frequency_3m::NUMERIC / NULLIF(p.freq_p95, 0), 1.0) * 100, 2)
        )) AS frequency_score,

        -- Monetary: higher = better
        GREATEST(0, LEAST(100,
            ROUND((LEAST(ra.monetary_3m / NULLIF(p.monetary_p95, 0), 1.0) * 100)::NUMERIC, 2)
        )) AS monetary_score,

        -- Return rate: lower = better (inverted)
        GREATEST(0, LEAST(100,
            ROUND(((1.0 - LEAST(
                CASE WHEN ra.total_txn_3m > 0
                    THEN ra.return_count_3m::NUMERIC / ra.total_txn_3m
                    ELSE 0
                END, 0.5) / 0.5) * 100)::NUMERIC, 2)
        )) AS return_score,

        -- Diversity: higher = better
        GREATEST(0, LEAST(100,
            ROUND(LEAST(ra.product_diversity::NUMERIC / NULLIF(p.diversity_p95, 0), 1.0) * 100, 2)
        )) AS diversity_score,

        -- Trend: improving/stable/declining
        CASE
            WHEN pa.frequency_prev IS NULL THEN 'new'
            WHEN ra.monetary_3m > pa.monetary_prev * 1.10 THEN 'improving'
            WHEN ra.monetary_3m < pa.monetary_prev * 0.90 THEN 'declining'
            ELSE 'stable'
        END AS trend

    FROM recent_activity ra
    LEFT JOIN recency r ON ra.customer_key = r.customer_key
    LEFT JOIN prior_activity pa ON ra.customer_key = pa.customer_key
    CROSS JOIN percentiles p
)

SELECT
    customer_key,
    customer_name,
    recency_days,
    frequency_3m,
    monetary_3m,
    product_diversity,
    return_rate,
    trend,

    -- Weighted composite health score
    GREATEST(0, LEAST(100, ROUND((
        recency_score   * 0.30 +
        frequency_score * 0.25 +
        monetary_score  * 0.25 +
        return_score    * 0.10 +
        diversity_score * 0.10
    )::NUMERIC, 2)))::NUMERIC(5,2) AS health_score,

    -- Health band
    CASE
        WHEN ROUND((recency_score * 0.30 + frequency_score * 0.25 + monetary_score * 0.25 + return_score * 0.10 + diversity_score * 0.10)::NUMERIC, 2) >= 80 THEN 'Thriving'
        WHEN ROUND((recency_score * 0.30 + frequency_score * 0.25 + monetary_score * 0.25 + return_score * 0.10 + diversity_score * 0.10)::NUMERIC, 2) >= 60 THEN 'Healthy'
        WHEN ROUND((recency_score * 0.30 + frequency_score * 0.25 + monetary_score * 0.25 + return_score * 0.10 + diversity_score * 0.10)::NUMERIC, 2) >= 40 THEN 'Needs Attention'
        WHEN ROUND((recency_score * 0.30 + frequency_score * 0.25 + monetary_score * 0.25 + return_score * 0.10 + diversity_score * 0.10)::NUMERIC, 2) >= 20 THEN 'At Risk'
        ELSE 'Critical'
    END AS health_band

FROM scored
