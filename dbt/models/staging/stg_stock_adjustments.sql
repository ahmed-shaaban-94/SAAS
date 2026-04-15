{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert',
        unique_key=['tenant_id', 'drug_code', 'site_code', 'adjustment_date', 'adjustment_type', 'batch_number'],
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

-- Silver layer: cleaned stock adjustments
-- Deduplicates by natural key, trims text fields, strips empty strings to NULL
-- Grain: one adjustment per (tenant, drug, site, date, type, batch)

WITH source AS (
    SELECT
        id,
        tenant_id,
        source_file,
        loaded_at,
        adjustment_date,
        adjustment_type,
        drug_code,
        site_code,
        batch_number,
        quantity,
        reason,
        authorized_by,
        notes
    FROM {{ ref('bronze_stock_adjustments') }}
    {% if is_incremental() %}
    WHERE loaded_at > (SELECT MAX(loaded_at) - INTERVAL '3 days' FROM {{ this }})
    {% endif %}
),

deduplicated AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY tenant_id, drug_code, site_code, adjustment_date, adjustment_type, batch_number
            ORDER BY id
        ) AS row_num
    FROM source
)

SELECT
    tenant_id,
    source_file,
    loaded_at,
    adjustment_date,
    NULLIF(TRIM(adjustment_type), '')       AS adjustment_type,
    NULLIF(TRIM(drug_code), '')             AS drug_code,
    NULLIF(TRIM(site_code), '')             AS site_code,
    NULLIF(TRIM(batch_number), '')          AS batch_number,
    COALESCE(quantity, 0)                   AS quantity,
    NULLIF(TRIM(reason), '')                AS reason,
    NULLIF(TRIM(authorized_by), '')         AS authorized_by,
    NULLIF(TRIM(notes), '')                 AS notes
FROM deduplicated
WHERE row_num = 1
