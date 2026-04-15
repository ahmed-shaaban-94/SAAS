{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert',
        unique_key=['tenant_id', 'drug_code', 'site_code', 'batch_number'],
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

-- Silver layer: cleaned batch master data
-- Deduplicates by natural batch key and keeps the latest loaded record

WITH ranked AS (
    SELECT
        tenant_id,
        source_file,
        loaded_at,
        NULLIF(TRIM(drug_code), '')                                  AS drug_code,
        NULLIF(TRIM(site_code), '')                                  AS site_code,
        NULLIF(TRIM(batch_number), '')                               AS batch_number,
        expiry_date,
        ROUND(initial_quantity, 4)                                   AS initial_quantity,
        ROUND(current_quantity, 4)                                   AS current_quantity,
        ROUND(unit_cost, 4)                                          AS unit_cost,
        COALESCE(NULLIF(TRIM(status), ''), 'active')                 AS status,
        quarantine_date,
        write_off_date,
        NULLIF(TRIM(write_off_reason), '')                           AS write_off_reason,
        NULLIF(TRIM(notes), '')                                      AS notes,
        ROW_NUMBER() OVER (
            PARTITION BY tenant_id, drug_code, site_code, batch_number
            ORDER BY loaded_at DESC, source_file DESC
        ) AS rn
    FROM {{ ref('bronze_batches') }}
    {% if is_incremental() %}
    WHERE loaded_at > (
        SELECT COALESCE(MAX(loaded_at), '1900-01-01'::timestamptz) - INTERVAL '3 days'
        FROM {{ this }}
    )
    {% endif %}
)

SELECT
    tenant_id,
    source_file,
    loaded_at,
    drug_code,
    site_code,
    batch_number,
    expiry_date,
    initial_quantity,
    current_quantity,
    unit_cost,
    status,
    quarantine_date,
    write_off_date,
    write_off_reason,
    notes,
    rn
FROM ranked
WHERE rn = 1
