{{
    config(
        materialized='incremental',
        unique_key=['tenant_id', 'po_number'],
        incremental_strategy='merge',
        schema='marts',
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE {{ this }} FORCE ROW LEVEL SECURITY",
            "DROP POLICY IF EXISTS owner_all ON {{ this }}",
            "CREATE POLICY owner_all ON {{ this }} FOR ALL TO datapulse USING (true) WITH CHECK (true)",
            "DROP POLICY IF EXISTS reader_tenant ON {{ this }}",
            "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)",
            "CREATE INDEX IF NOT EXISTS idx_fct_po_tenant_supplier ON {{ this }} (tenant_id, supplier_key)",
            "CREATE INDEX IF NOT EXISTS idx_fct_po_tenant_status ON {{ this }} (tenant_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_fct_po_po_date ON {{ this }} (po_date DESC)"
        ]
    )
}}

-- Purchase Orders fact table
-- Grain: one row per purchase order (header level)
-- Joins to dim_supplier and dim_site for surrogate keys
-- Aggregates line totals and delivery performance from po_lines

WITH po AS (
    SELECT *
    FROM {{ ref('stg_purchase_orders') }}
    {% if is_incremental() %}
    WHERE loaded_at > (SELECT MAX(loaded_at) FROM {{ this }})
    {% endif %}
),

lines_agg AS (
    SELECT
        tenant_id,
        po_number,
        SUM(ordered_quantity * unit_price)::NUMERIC(18, 4)  AS total_ordered_value,
        SUM(received_quantity * unit_price)::NUMERIC(18, 4) AS total_received_value,
        COUNT(line_number)::INT                             AS line_count,
        MAX(loaded_at)                                      AS lines_loaded_at
    FROM {{ ref('stg_po_lines') }}
    GROUP BY tenant_id, po_number
),

dim_sup AS (
    SELECT supplier_key, tenant_id, supplier_code
    FROM {{ ref('dim_supplier') }}
),

dim_s AS (
    SELECT site_key, tenant_id, site_code
    FROM {{ ref('dim_site') }}
)

SELECT
    po.tenant_id,
    COALESCE(sup.supplier_key, -1)                          AS supplier_key,
    COALESCE(s.site_key, -1)                                AS site_key,
    po.po_number,
    po.po_date,
    po.status,
    po.expected_date,
    po.supplier_code,
    po.site_code,
    COALESCE(la.total_ordered_value, 0)                     AS total_ordered_value,
    COALESCE(la.total_received_value, 0)                    AS total_received_value,
    COALESCE(la.line_count, 0)                              AS line_count,
    -- Delivery performance: actual lead days for received POs
    CASE
        WHEN po.status = 'received' AND po.expected_date IS NOT NULL
        THEN (po.expected_date - po.po_date)
        ELSE NULL
    END                                                     AS actual_lead_days,
    po.notes,
    po.created_by,
    po.loaded_at
FROM po
LEFT JOIN lines_agg la ON po.po_number = la.po_number AND po.tenant_id = la.tenant_id
LEFT JOIN dim_sup sup ON po.supplier_code = sup.supplier_code AND po.tenant_id = sup.tenant_id
LEFT JOIN dim_s s ON po.site_code = s.site_code AND po.tenant_id = s.tenant_id
