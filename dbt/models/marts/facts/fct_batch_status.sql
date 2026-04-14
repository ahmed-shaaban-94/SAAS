{{
    config(
        materialized='incremental',
        unique_key='event_key',
        incremental_strategy='merge',
        on_schema_change='append_new_columns',
        schema='marts',
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE {{ this }} FORCE ROW LEVEL SECURITY",
            "DROP POLICY IF EXISTS owner_all ON {{ this }}",
            "CREATE POLICY owner_all ON {{ this }} FOR ALL TO datapulse USING (true) WITH CHECK (true)",
            "DROP POLICY IF EXISTS reader_tenant ON {{ this }}",
            "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)",
            "CREATE INDEX IF NOT EXISTS idx_fct_batch_status_tenant ON {{ this }} (tenant_id)",
            "CREATE INDEX IF NOT EXISTS idx_fct_batch_status_batch ON {{ this }} (batch_key)",
            "CREATE INDEX IF NOT EXISTS idx_fct_batch_status_event_date ON {{ this }} (event_date)",
            "CREATE INDEX IF NOT EXISTS idx_fct_batch_status_event_type ON {{ this }} (event_type)"
        ]
    )
}}

-- Batch lifecycle events
-- Grain: one lifecycle event per batch

WITH batches AS (
    SELECT *
    FROM {{ ref('dim_batch') }}
    WHERE batch_key != -1
    {% if is_incremental() %}
    AND loaded_at >= (
        SELECT COALESCE(MAX(loaded_at), '1900-01-01'::timestamptz) - INTERVAL '7 days'
        FROM {{ this }}
    )
    {% endif %}
),

events AS (
    SELECT
        tenant_id,
        batch_key,
        drug_code,
        site_code,
        loaded_at::date AS event_date,
        'received' AS event_type,
        initial_quantity AS quantity,
        unit_cost,
        NULL::TEXT AS event_reason,
        loaded_at
    FROM batches

    UNION ALL

    SELECT
        tenant_id,
        batch_key,
        drug_code,
        site_code,
        GREATEST(loaded_at::date, expiry_date - 30) AS event_date,
        'near_expiry' AS event_type,
        current_quantity AS quantity,
        unit_cost,
        NULL::TEXT AS event_reason,
        loaded_at
    FROM batches
    WHERE expiry_date IS NOT NULL

    UNION ALL

    SELECT
        tenant_id,
        batch_key,
        drug_code,
        site_code,
        expiry_date AS event_date,
        'expired' AS event_type,
        current_quantity AS quantity,
        unit_cost,
        NULL::TEXT AS event_reason,
        loaded_at
    FROM batches
    WHERE expiry_date IS NOT NULL

    UNION ALL

    SELECT
        tenant_id,
        batch_key,
        drug_code,
        site_code,
        quarantine_date AS event_date,
        'quarantined' AS event_type,
        current_quantity AS quantity,
        unit_cost,
        notes AS event_reason,
        loaded_at
    FROM batches
    WHERE quarantine_date IS NOT NULL

    UNION ALL

    SELECT
        tenant_id,
        batch_key,
        drug_code,
        site_code,
        write_off_date AS event_date,
        'written_off' AS event_type,
        current_quantity AS quantity,
        unit_cost,
        write_off_reason AS event_reason,
        loaded_at
    FROM batches
    WHERE write_off_date IS NOT NULL
),

with_keys AS (
    SELECT
        ('x' || LEFT(MD5(
            COALESCE(e.tenant_id::TEXT, '') || '|' ||
            COALESCE(e.batch_key::TEXT, '') || '|' ||
            COALESCE(e.event_type, '') || '|' ||
            COALESCE(e.event_date::TEXT, '')
        ), 16))::BIT(64)::BIGINT AS event_key,
        e.tenant_id,
        e.batch_key,
        COALESCE(p.product_key, -1) AS product_key,
        COALESCE(s.site_key, -1) AS site_key,
        COALESCE(d.date_key, -1) AS date_key,
        e.event_date,
        e.event_type,
        ROUND(e.quantity, 4) AS quantity,
        ROUND(e.unit_cost, 4) AS unit_cost,
        e.event_reason,
        e.loaded_at
    FROM events e
    LEFT JOIN {{ ref('dim_batch') }}  b ON e.batch_key = b.batch_key AND e.tenant_id = b.tenant_id
    LEFT JOIN {{ ref('dim_product') }} p ON b.drug_code = p.drug_code AND e.tenant_id = p.tenant_id
    LEFT JOIN {{ ref('dim_site') }}    s ON b.site_code = s.site_code AND e.tenant_id = s.tenant_id
    LEFT JOIN {{ ref('dim_date') }}    d ON e.event_date = d.full_date
)

SELECT * FROM with_keys
