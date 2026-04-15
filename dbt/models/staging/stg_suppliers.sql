{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert',
        unique_key=['tenant_id', 'supplier_code'],
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

-- Silver layer: cleaned supplier directory
-- SCD Type 1: latest record per (tenant_id, supplier_code)
-- Trims text, coerces is_active to boolean, removes duplicates

WITH source AS (
    SELECT *
    FROM {{ source('bronze', 'suppliers') }}
    {% if is_incremental() %}
    WHERE loaded_at > (SELECT MAX(loaded_at) - INTERVAL '3 days' FROM {{ this }})
    {% endif %}
),

deduplicated AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY tenant_id, supplier_code
            ORDER BY loaded_at DESC
        ) AS rn
    FROM source
)

SELECT
    tenant_id,
    TRIM(supplier_code)                                             AS supplier_code,
    COALESCE(NULLIF(TRIM(supplier_name), ''), 'Unknown')           AS supplier_name,
    NULLIF(TRIM(COALESCE(contact_name, '')), '')                   AS contact_name,
    NULLIF(TRIM(COALESCE(contact_phone, '')), '')                  AS contact_phone,
    NULLIF(TRIM(COALESCE(contact_email, '')), '')                  AS contact_email,
    NULLIF(TRIM(COALESCE(address, '')), '')                        AS address,
    COALESCE(payment_terms_days, 30)                               AS payment_terms_days,
    COALESCE(lead_time_days, 7)                                    AS lead_time_days,
    COALESCE(is_active, TRUE)                                      AS is_active,
    NULLIF(TRIM(COALESCE(notes, '')), '')                          AS notes,
    source_file,
    loaded_at
FROM deduplicated
WHERE rn = 1
  AND supplier_code IS NOT NULL
  AND TRIM(supplier_code) != ''
