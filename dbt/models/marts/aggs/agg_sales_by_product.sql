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
            "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)",
            "CREATE INDEX IF NOT EXISTS idx_agg_sales_by_product_year_month ON {{ this }} (year, month)",
            "CREATE INDEX IF NOT EXISTS idx_agg_sales_by_product_product_key ON {{ this }} (product_key)"
        ]
    )
}}

-- Product sales aggregation with denormalized product attributes
-- Grain: one row per (product_key, year, month)

WITH product_monthly AS (
    SELECT
        f.tenant_id,
        f.product_key,
        d.year,
        d.month,
        d.month_name,
        SUM(f.quantity)::NUMERIC(18,4)                                          AS total_quantity,
        COALESCE(SUM(f.quantity) FILTER (WHERE f.is_return), 0)::NUMERIC(18,4)  AS return_quantity,
        ROUND(SUM(f.sales), 2)                                                  AS total_sales,
        ROUND(SUM(f.discount), 2)                                               AS total_discount,
        COUNT(*)::INT                                                           AS transaction_count,
        COUNT(*) FILTER (WHERE f.is_return)::INT                                AS return_count,
        COUNT(DISTINCT f.customer_key)::INT                                     AS unique_customers,
        COUNT(DISTINCT f.site_key)::INT                                         AS unique_sites,
        ROUND(
            SUM(f.sales) / NULLIF(COUNT(DISTINCT f.invoice_id), 0),
            2
        )                                                                       AS avg_basket_size
    FROM {{ ref('fct_sales') }} f
    INNER JOIN {{ ref('dim_date') }} d ON f.date_key = d.date_key
    GROUP BY f.tenant_id, f.product_key, d.year, d.month, d.month_name
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
    r.tenant_id,
    r.product_key,
    p.drug_code,
    p.drug_name,
    p.drug_brand,
    p.drug_category,
    p.drug_division,
    p.drug_cluster,
    p.origin,
    r.year,
    r.month,
    r.month_name,
    r.total_quantity,
    r.return_quantity,
    r.total_sales,
    r.total_discount,
    r.transaction_count,
    r.return_count,
    r.return_rate,
    r.unique_customers,
    r.unique_sites,
    r.avg_basket_size
FROM with_rate r
INNER JOIN {{ ref('dim_product') }} p ON r.product_key = p.product_key AND r.tenant_id = p.tenant_id
