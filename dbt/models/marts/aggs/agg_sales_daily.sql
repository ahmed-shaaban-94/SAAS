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
            "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)"
        ]
    )
}}

-- Daily sales aggregation
-- Grain: one row per (tenant_id, date_key, site_key, billing_way)

WITH daily AS (
    SELECT
        f.tenant_id,
        f.date_key,
        f.site_key,
        f.billing_way,
        SUM(f.quantity)::NUMERIC(18,4)           AS total_quantity,
        ROUND(SUM(f.sales), 2)                   AS total_sales,
        ROUND(SUM(f.discount), 2)                AS total_discount,
        ROUND(SUM(f.net_amount), 2)              AS total_net_amount,
        COUNT(*)::INT                            AS transaction_count,
        COUNT(*) FILTER (WHERE f.is_return)::INT AS return_count,
        COUNT(DISTINCT f.customer_key)::INT      AS unique_customers,
        COUNT(DISTINCT f.product_key)::INT       AS unique_products,
        ROUND(
            SUM(f.net_amount) / NULLIF(COUNT(DISTINCT f.invoice_id), 0),
            2
        )                                        AS avg_basket_size
    FROM {{ ref('fct_sales') }} f
    GROUP BY f.tenant_id, f.date_key, f.site_key, f.billing_way
)

SELECT * FROM daily
