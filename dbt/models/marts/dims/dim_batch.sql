{{
    config(
        materialized='incremental',
        unique_key=['tenant_id', 'batch_key'],
        incremental_strategy='merge',
        schema='marts',
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE {{ this }} FORCE ROW LEVEL SECURITY",
            "DROP POLICY IF EXISTS owner_all ON {{ this }}",
            "CREATE POLICY owner_all ON {{ this }} FOR ALL TO datapulse USING (true) WITH CHECK (true)",
            "DROP POLICY IF EXISTS reader_tenant ON {{ this }}",
            "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)",
            "CREATE INDEX IF NOT EXISTS idx_dim_batch_drug_code_tenant ON {{ this }} (drug_code, tenant_id)",
            "CREATE INDEX IF NOT EXISTS idx_dim_batch_expiry ON {{ this }} (expiry_date)",
            "CREATE INDEX IF NOT EXISTS idx_dim_batch_status ON {{ this }} (status)"
        ]
    )
}}

-- Batch dimension: one row per unique batch per drug per site
-- SCD Type 1: latest attributes win
-- batch_key = deterministic MD5 surrogate

WITH ranked AS (
    SELECT
        tenant_id,
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
        (expiry_date - CURRENT_DATE) AS days_to_expiry,
        CASE
            WHEN status IN ('expired', 'written_off', 'quarantined') THEN status
            WHEN expiry_date < CURRENT_DATE THEN 'expired'
            WHEN expiry_date <= CURRENT_DATE + 30 THEN 'near_expiry'
            ELSE 'active'
        END AS computed_status,
        loaded_at,
        ROW_NUMBER() OVER (
            PARTITION BY tenant_id, drug_code, site_code, batch_number
            ORDER BY loaded_at DESC
        ) AS rn
    FROM {{ ref('stg_batches') }}
    WHERE drug_code IS NOT NULL
      AND site_code IS NOT NULL
      AND batch_number IS NOT NULL
    {% if is_incremental() %}
      AND loaded_at >= (
        SELECT COALESCE(MAX(loaded_at), '1900-01-01'::timestamptz) - INTERVAL '7 days'
        FROM {{ this }}
      )
    {% endif %}
),

final AS (
    SELECT
        ABS(('x' || LEFT(MD5(
            r.tenant_id::TEXT || '|' || r.drug_code || '|' || r.site_code || '|' || r.batch_number
        ), 8))::BIT(32)::INT) AS batch_key,
        r.tenant_id,
        r.drug_code,
        r.site_code,
        r.batch_number,
        r.expiry_date,
        r.initial_quantity,
        r.current_quantity,
        r.unit_cost,
        r.status,
        r.quarantine_date,
        r.write_off_date,
        r.write_off_reason,
        r.notes,
        r.days_to_expiry,
        r.computed_status,
        r.loaded_at,
        r.rn
    FROM ranked r
    WHERE r.rn = 1
)

SELECT
    batch_key,
    tenant_id,
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
    days_to_expiry,
    computed_status,
    loaded_at,
    rn
FROM final

{% if not is_incremental() %}
UNION ALL

SELECT
    -1                  AS batch_key,
    t.tenant_id,
    '__UNKNOWN__'       AS drug_code,
    '__UNKNOWN__'       AS site_code,
    '__UNKNOWN__'       AS batch_number,
    NULL                AS expiry_date,
    0                   AS initial_quantity,
    0                   AS current_quantity,
    NULL                AS unit_cost,
    'active'            AS status,
    NULL                AS quarantine_date,
    NULL                AS write_off_date,
    NULL                AS write_off_reason,
    NULL                AS notes,
    0                   AS days_to_expiry,
    'active'            AS computed_status,
    now()               AS loaded_at,
    1                   AS rn
FROM (SELECT DISTINCT tenant_id FROM {{ ref('stg_batches') }}) t
{% endif %}
