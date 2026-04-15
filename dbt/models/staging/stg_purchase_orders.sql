{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert',
        unique_key=['tenant_id', 'po_number'],
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

-- Silver layer: cleaned purchase order headers
-- SCD Type 1: latest record per (tenant_id, po_number)
-- Validates status enum, trims text, coerces dates

WITH source AS (
    SELECT *
    FROM {{ source('bronze', 'purchase_orders') }}
    {% if is_incremental() %}
    WHERE loaded_at > (SELECT MAX(loaded_at) - INTERVAL '3 days' FROM {{ this }})
    {% endif %}
),

deduplicated AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY tenant_id, po_number
            ORDER BY loaded_at DESC
        ) AS rn
    FROM source
)

SELECT
    tenant_id,
    TRIM(po_number)                                                                AS po_number,
    po_date,
    TRIM(supplier_code)                                                            AS supplier_code,
    TRIM(site_code)                                                                AS site_code,
    CASE
        WHEN LOWER(TRIM(COALESCE(status, ''))) IN
             ('draft', 'submitted', 'partial', 'received', 'cancelled')
        THEN LOWER(TRIM(status))
        ELSE 'draft'
    END                                                                            AS status,
    expected_date,
    COALESCE(total_amount, 0)::NUMERIC(18, 4)                                      AS total_amount,
    NULLIF(TRIM(COALESCE(notes, '')), '')                                          AS notes,
    NULLIF(TRIM(COALESCE(created_by, '')), '')                                    AS created_by,
    source_file,
    loaded_at
FROM deduplicated
WHERE rn = 1
  AND po_number IS NOT NULL
  AND TRIM(po_number) != ''
  AND po_date IS NOT NULL
