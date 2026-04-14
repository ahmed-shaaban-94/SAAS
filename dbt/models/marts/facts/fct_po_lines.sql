{{
    config(
        materialized='incremental',
        unique_key=['tenant_id', 'po_number', 'line_number'],
        incremental_strategy='merge',
        schema='marts',
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE {{ this }} FORCE ROW LEVEL SECURITY",
            "DROP POLICY IF EXISTS owner_all ON {{ this }}",
            "CREATE POLICY owner_all ON {{ this }} FOR ALL TO datapulse USING (true) WITH CHECK (true)",
            "DROP POLICY IF EXISTS reader_tenant ON {{ this }}",
            "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)",
            "CREATE INDEX IF NOT EXISTS idx_fct_po_lines_tenant_drug ON {{ this }} (tenant_id, product_key)",
            "CREATE INDEX IF NOT EXISTS idx_fct_po_lines_tenant_supplier ON {{ this }} (tenant_id, supplier_key)",
            "CREATE INDEX IF NOT EXISTS idx_fct_po_lines_drug_code ON {{ this }} (drug_code, tenant_id)"
        ]
    )
}}

-- Purchase Order Lines fact table
-- Grain: one row per PO line item
-- Joins to dim_product (for product_key) and dim_supplier (via PO header)

WITH lines AS (
    SELECT *
    FROM {{ ref('stg_po_lines') }}
    {% if is_incremental() %}
    WHERE loaded_at > (SELECT MAX(loaded_at) FROM {{ this }})
    {% endif %}
),

po_headers AS (
    SELECT po_number, tenant_id, supplier_code, po_date, site_code
    FROM {{ ref('stg_purchase_orders') }}
),

dim_prod AS (
    SELECT product_key, tenant_id, drug_code
    FROM {{ ref('dim_product') }}
),

dim_sup AS (
    SELECT supplier_key, tenant_id, supplier_code
    FROM {{ ref('dim_supplier') }}
)

SELECT
    l.tenant_id,
    COALESCE(p.product_key, -1)                              AS product_key,
    COALESCE(sup.supplier_key, -1)                           AS supplier_key,
    l.po_number,
    l.line_number,
    l.drug_code,
    po.supplier_code,
    po.po_date,
    l.ordered_quantity,
    l.unit_price,
    l.received_quantity,
    l.line_total,
    l.fulfillment_pct,
    l.loaded_at
FROM lines l
LEFT JOIN po_headers po ON l.po_number = po.po_number AND l.tenant_id = po.tenant_id
LEFT JOIN dim_prod p ON l.drug_code = p.drug_code AND l.tenant_id = p.tenant_id
LEFT JOIN dim_sup sup ON po.supplier_code = sup.supplier_code AND l.tenant_id = sup.tenant_id
