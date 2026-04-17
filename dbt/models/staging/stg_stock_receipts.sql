{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert',
        unique_key=['tenant_id', 'receipt_reference', 'drug_code', 'site_code', 'batch_number'],
        on_schema_change='sync_all_columns',
        schema='staging',
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

-- Silver layer: cleaned stock receipts
-- Deduplicates by natural key, trims text fields, strips empty strings to NULL
-- Grain: one receipt line per (tenant, receipt_reference, drug, site, batch)

WITH source AS (
    SELECT
        id,
        tenant_id,
        source_file,
        loaded_at,
        receipt_date,
        receipt_reference,
        drug_code,
        site_code,
        batch_number,
        expiry_date,
        quantity,
        unit_cost,
        supplier_code,
        po_reference,
        notes
    FROM {{ ref('bronze_stock_receipts') }}
    {% if is_incremental() %}
    WHERE loaded_at > (SELECT MAX(loaded_at) - INTERVAL '3 days' FROM {{ this }})
    {% endif %}
),

deduplicated AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY tenant_id, receipt_reference, drug_code, site_code, batch_number
            ORDER BY id
        ) AS row_num
    FROM source
)

SELECT
    tenant_id,
    source_file,
    loaded_at,
    receipt_date,
    NULLIF(TRIM(receipt_reference), '')     AS receipt_reference,
    NULLIF(TRIM(drug_code), '')             AS drug_code,
    NULLIF(TRIM(site_code), '')             AS site_code,
    NULLIF(TRIM(batch_number), '')          AS batch_number,
    expiry_date,
    COALESCE(quantity, 0)                   AS quantity,
    unit_cost,
    NULLIF(TRIM(supplier_code), '')         AS supplier_code,
    NULLIF(TRIM(po_reference), '')          AS po_reference,
    NULLIF(TRIM(notes), '')                 AS notes
FROM deduplicated
WHERE row_num = 1
