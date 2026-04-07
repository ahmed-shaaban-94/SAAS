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
            "CREATE INDEX IF NOT EXISTS idx_feat_product_affinity_a ON {{ this }} (tenant_id, product_key_a)",
            "CREATE INDEX IF NOT EXISTS idx_feat_product_affinity_b ON {{ this }} (tenant_id, product_key_b)"
        ]
    )
}}

-- Product affinity / cross-sell analysis
-- Grain: one row per (tenant_id, product_key_a, product_key_b) where a < b
-- Shows how often products are purchased together on the same invoice

WITH invoice_products AS (
    SELECT DISTINCT
        tenant_id,
        invoice_id,
        product_key
    FROM {{ ref('fct_sales') }}
    WHERE product_key > 0
      AND NOT is_return
),

total_invoices AS (
    SELECT
        tenant_id,
        COUNT(DISTINCT invoice_id) AS total
    FROM invoice_products
    GROUP BY tenant_id
),

product_invoice_counts AS (
    SELECT
        tenant_id,
        product_key,
        COUNT(DISTINCT invoice_id) AS invoice_count
    FROM invoice_products
    GROUP BY tenant_id, product_key
),

pairs AS (
    SELECT
        a.tenant_id,
        a.product_key AS product_key_a,
        b.product_key AS product_key_b,
        COUNT(DISTINCT a.invoice_id) AS co_occurrence_count
    FROM invoice_products a
    JOIN invoice_products b
        ON a.tenant_id = b.tenant_id
        AND a.invoice_id = b.invoice_id
        AND a.product_key < b.product_key
    GROUP BY a.tenant_id, a.product_key, b.product_key
    HAVING COUNT(DISTINCT a.invoice_id) >= 5
)

SELECT
    p.tenant_id,
    p.product_key_a,
    pa.drug_name AS product_name_a,
    p.product_key_b,
    pb.drug_name AS product_name_b,
    p.co_occurrence_count,
    ROUND(p.co_occurrence_count::NUMERIC / t.total * 100, 4) AS support_pct,
    ROUND(p.co_occurrence_count::NUMERIC / ca.invoice_count * 100, 2) AS confidence_a_to_b,
    ROUND(p.co_occurrence_count::NUMERIC / cb.invoice_count * 100, 2) AS confidence_b_to_a
FROM pairs p
JOIN total_invoices t ON p.tenant_id = t.tenant_id
JOIN product_invoice_counts ca ON p.tenant_id = ca.tenant_id AND p.product_key_a = ca.product_key
JOIN product_invoice_counts cb ON p.tenant_id = cb.tenant_id AND p.product_key_b = cb.product_key
JOIN {{ ref('dim_product') }} pa ON p.tenant_id = pa.tenant_id AND p.product_key_a = pa.product_key
JOIN {{ ref('dim_product') }} pb ON p.tenant_id = pb.tenant_id AND p.product_key_b = pb.product_key
