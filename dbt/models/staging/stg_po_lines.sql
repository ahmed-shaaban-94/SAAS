{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert',
        unique_key=['tenant_id', 'po_number', 'line_number'],
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

-- Silver layer: cleaned purchase order line items
-- Unique key: (tenant_id, po_number, line_number)
-- Validates non-negative quantities, coerces numeric types

WITH source AS (
    SELECT *
    FROM {{ source('bronze', 'po_lines') }}
    {% if is_incremental() %}
    WHERE loaded_at > (SELECT MAX(loaded_at) - INTERVAL '3 days' FROM {{ this }})
    {% endif %}
),

deduplicated AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY tenant_id, po_number, line_number
            ORDER BY loaded_at DESC
        ) AS rn
    FROM source
)

SELECT
    tenant_id,
    TRIM(po_number)                                             AS po_number,
    line_number,
    TRIM(drug_code)                                             AS drug_code,
    GREATEST(COALESCE(ordered_quantity, 0)::NUMERIC(18, 4), 0) AS ordered_quantity,
    GREATEST(COALESCE(unit_price, 0)::NUMERIC(18, 4), 0)       AS unit_price,
    GREATEST(COALESCE(received_quantity, 0)::NUMERIC(18, 4), 0) AS received_quantity,
    -- Derived: line total (ordered * price)
    GREATEST(COALESCE(ordered_quantity, 0), 0)::NUMERIC(18, 4)
        * GREATEST(COALESCE(unit_price, 0), 0)::NUMERIC(18, 4) AS line_total,
    -- Derived: fulfillment percentage
    ROUND(
        GREATEST(COALESCE(received_quantity, 0), 0)::NUMERIC
        / NULLIF(GREATEST(COALESCE(ordered_quantity, 0), 0), 0),
        4
    )                                                           AS fulfillment_pct,
    loaded_at
FROM deduplicated
WHERE rn = 1
  AND po_number IS NOT NULL
  AND TRIM(po_number) != ''
  AND line_number IS NOT NULL
  AND drug_code IS NOT NULL
  AND TRIM(drug_code) != ''
