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
            "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = (SELECT NULLIF(current_setting('app.tenant_id', true), '')::INT))",
            "CREATE INDEX IF NOT EXISTS idx_feat_customer_segments_customer_key ON {{ this }} (tenant_id, customer_key)",
            "CREATE INDEX IF NOT EXISTS idx_feat_customer_segments_segment ON {{ this }} (tenant_id, rfm_segment)"
        ]
    )
}}

-- Customer RFM segmentation for analytics dashboards
-- Grain: one row per (tenant_id, customer_key)
-- RFM = Recency, Frequency, Monetary — quintile scoring (1-5, higher = better)

WITH customer_rfm_raw AS (
    SELECT
        f.tenant_id,
        f.customer_key,
        c.customer_id,
        c.customer_name,
        -- Recency: days since last purchase
        (CURRENT_DATE - MAX(d.full_date))::INT             AS days_since_last,
        -- Frequency: distinct invoices
        COUNT(DISTINCT f.invoice_id)::INT                  AS frequency,
        -- Monetary: total net spend
        ROUND(SUM(f.sales), 2)                              AS monetary,
        -- Additional context
        MIN(d.full_date)                                   AS first_purchase_date,
        MAX(d.full_date)                                   AS last_purchase_date,
        (MAX(d.full_date) - MIN(d.full_date))::INT         AS lifetime_days,
        ROUND(
            SUM(f.sales) / NULLIF(COUNT(DISTINCT f.invoice_id), 0),
            2
        )                                                  AS avg_basket_size,
        COUNT(DISTINCT f.product_key)::INT                 AS unique_products,
        COUNT(*) FILTER (WHERE f.is_return)::INT           AS return_count,
        COUNT(*)::INT                                      AS transaction_count
    FROM {{ ref('fct_sales') }} f
    INNER JOIN {{ ref('dim_date') }} d ON f.date_key = d.date_key
    INNER JOIN {{ ref('dim_customer') }} c ON f.customer_key = c.customer_key AND f.tenant_id = c.tenant_id
    WHERE f.customer_key != -1
    GROUP BY f.tenant_id, f.customer_key, c.customer_id, c.customer_name
),

with_ntiles AS (
    SELECT
        r.*,
        -- Higher score = better (recency: lower days = higher score)
        NTILE(5) OVER (PARTITION BY r.tenant_id ORDER BY r.days_since_last DESC) AS r_score,
        NTILE(5) OVER (PARTITION BY r.tenant_id ORDER BY r.frequency ASC)        AS f_score,
        NTILE(5) OVER (PARTITION BY r.tenant_id ORDER BY r.monetary ASC)         AS m_score
    FROM customer_rfm_raw r
)

SELECT
    n.tenant_id,
    n.customer_key,
    n.customer_id,
    n.customer_name,
    n.days_since_last,
    n.frequency,
    n.monetary,
    n.first_purchase_date,
    n.last_purchase_date,
    n.lifetime_days,
    n.avg_basket_size,
    n.unique_products,
    n.return_count,
    n.transaction_count,
    n.r_score,
    n.f_score,
    n.m_score,
    CASE
        WHEN n.r_score >= 4 AND n.f_score >= 4 AND n.m_score >= 4 THEN 'Champion'
        WHEN n.r_score >= 4 AND n.f_score >= 3                    THEN 'Loyal'
        WHEN n.r_score >= 4 AND n.f_score <= 2                    THEN 'New'
        WHEN n.r_score <= 2 AND n.f_score >= 3                    THEN 'At Risk'
        WHEN n.r_score <= 2 AND n.f_score <= 2 AND n.m_score >= 3 THEN 'Cant Lose'
        WHEN n.r_score <= 2                                        THEN 'Hibernating'
        ELSE 'Potential Loyalist'
    END AS rfm_segment,
    ROUND(
        n.return_count::NUMERIC / NULLIF(n.transaction_count, 0),
        4
    ) AS return_rate
FROM with_ntiles n
