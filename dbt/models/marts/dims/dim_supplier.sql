{{
    config(
        materialized='incremental',
        unique_key=['tenant_id', 'supplier_key'],
        incremental_strategy='merge',
        schema='marts',
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE {{ this }} FORCE ROW LEVEL SECURITY",
            "DROP POLICY IF EXISTS owner_all ON {{ this }}",
            "CREATE POLICY owner_all ON {{ this }} FOR ALL TO datapulse USING (true) WITH CHECK (true)",
            "DROP POLICY IF EXISTS reader_tenant ON {{ this }}",
            "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)",
            "CREATE INDEX IF NOT EXISTS idx_dim_supplier_code_tenant ON {{ this }} (supplier_code, tenant_id)",
            "CREATE INDEX IF NOT EXISTS idx_dim_supplier_key ON {{ this }} (supplier_key)"
        ]
    )
}}

-- Supplier dimension
-- SCD Type 1: latest attributes win (by most recent loaded_at)
-- supplier_key = ABS(MD5(tenant_id || '|' || supplier_code)) truncated to 32-bit int
-- -1 row reserved for Unknown/Unassigned (on full refresh only)

WITH ranked AS (
    SELECT
        tenant_id,
        supplier_code,
        supplier_name,
        contact_name,
        contact_phone,
        contact_email,
        address,
        payment_terms_days,
        lead_time_days,
        is_active,
        notes,
        loaded_at,
        ROW_NUMBER() OVER (
            PARTITION BY tenant_id, supplier_code
            ORDER BY loaded_at DESC
        ) AS rn
    FROM {{ ref('stg_suppliers') }}
    {% if is_incremental() %}
    WHERE loaded_at >= (SELECT MAX(loaded_at) - INTERVAL '7 days' FROM {{ ref('stg_suppliers') }})
    {% endif %}
)

SELECT
    ABS(('x' || LEFT(MD5(r.tenant_id::TEXT || '|' || r.supplier_code), 8))::BIT(32)::INT)
        AS supplier_key,
    r.tenant_id,
    r.supplier_code,
    r.supplier_name,
    r.contact_name,
    r.contact_phone,
    r.contact_email,
    r.address,
    r.payment_terms_days,
    r.lead_time_days,
    r.is_active,
    r.notes,
    r.loaded_at
FROM ranked r
WHERE r.rn = 1

{% if not is_incremental() %}
UNION ALL

SELECT
    -1                AS supplier_key,
    t.tenant_id,
    '__UNKNOWN__'     AS supplier_code,
    'Unknown'         AS supplier_name,
    NULL              AS contact_name,
    NULL              AS contact_phone,
    NULL              AS contact_email,
    NULL              AS address,
    0                 AS payment_terms_days,
    0                 AS lead_time_days,
    FALSE             AS is_active,
    NULL              AS notes,
    NOW()             AS loaded_at
FROM (SELECT DISTINCT tenant_id FROM {{ ref('stg_suppliers') }}) t
{% endif %}
