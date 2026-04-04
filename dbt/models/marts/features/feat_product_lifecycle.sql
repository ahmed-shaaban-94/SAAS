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
            "CREATE INDEX IF NOT EXISTS idx_feat_product_lifecycle_product_key ON {{ this }} (tenant_id, product_key)",
            "CREATE INDEX IF NOT EXISTS idx_feat_product_lifecycle_phase ON {{ this }} (tenant_id, lifecycle_phase)"
        ]
    )
}}

-- Product lifecycle classification for analytics + forecasting
-- Grain: one row per (tenant_id, product_key)
-- Classifies products: Growth, Mature, Decline, Dormant

WITH product_quarterly AS (
    SELECT
        tenant_id,
        product_key,
        drug_code,
        drug_name,
        drug_brand,
        drug_category,
        year,
        CEIL(month / 3.0)::INT AS quarter,
        SUM(total_sales)       AS quarterly_revenue,
        SUM(total_quantity)    AS quarterly_quantity,
        SUM(transaction_count) AS quarterly_txn
    FROM {{ ref('agg_sales_by_product') }}
    GROUP BY tenant_id, product_key, drug_code, drug_name, drug_brand, drug_category, year, CEIL(month / 3.0)::INT
),

with_qoq AS (
    SELECT
        pq.*,
        LAG(pq.quarterly_revenue, 1) OVER (
            PARTITION BY pq.tenant_id, pq.product_key ORDER BY pq.year, pq.quarter
        ) AS prev_quarter_revenue,
        ROW_NUMBER() OVER (
            PARTITION BY pq.tenant_id, pq.product_key ORDER BY pq.year DESC, pq.quarter DESC
        ) AS recency_rank
    FROM product_quarterly pq
),

growth_calc AS (
    SELECT
        tenant_id,
        product_key,
        MIN(drug_code)     AS drug_code,
        MIN(drug_name)     AS drug_name,
        MIN(drug_brand)    AS drug_brand,
        MIN(drug_category) AS drug_category,
        -- Recent growth: average QoQ growth over last 4 quarters
        ROUND(
            AVG(
                CASE WHEN recency_rank <= 4 AND prev_quarter_revenue IS NOT NULL
                     THEN (quarterly_revenue - prev_quarter_revenue) / NULLIF(prev_quarter_revenue, 0)
                END
            ),
            4
        ) AS avg_recent_growth,
        -- Lifetime metrics
        COUNT(DISTINCT (year, quarter))::INT AS quarters_active,
        ROUND(SUM(quarterly_revenue), 2)     AS total_lifetime_revenue,
        ROUND(SUM(quarterly_quantity), 2)     AS total_lifetime_quantity,
        MIN(year || '-Q' || quarter)          AS first_sale_quarter,
        MAX(year || '-Q' || quarter)          AS last_sale_quarter,
        -- Most recent quarter info
        MAX(CASE WHEN recency_rank = 1 THEN year END)    AS last_year,
        MAX(CASE WHEN recency_rank = 1 THEN quarter END) AS last_quarter
    FROM with_qoq
    GROUP BY tenant_id, product_key
)

SELECT
    g.tenant_id,
    g.product_key,
    g.drug_code,
    g.drug_name,
    g.drug_brand,
    g.drug_category,
    g.avg_recent_growth,
    g.quarters_active,
    g.total_lifetime_revenue,
    g.total_lifetime_quantity,
    g.first_sale_quarter,
    g.last_sale_quarter,
    CASE
        -- Dormant: last sale was more than 1 quarter ago (approximate)
        WHEN g.last_year < EXTRACT(YEAR FROM CURRENT_DATE)::INT
             OR (g.last_year = EXTRACT(YEAR FROM CURRENT_DATE)::INT
                 AND g.last_quarter < CEIL(EXTRACT(MONTH FROM CURRENT_DATE) / 3.0)::INT - 1)
            THEN 'Dormant'
        WHEN g.avg_recent_growth > 0.10 THEN 'Growth'
        WHEN g.avg_recent_growth >= -0.05 THEN 'Mature'
        WHEN g.avg_recent_growth < -0.05 THEN 'Decline'
        ELSE 'Mature'
    END AS lifecycle_phase
FROM growth_calc g
