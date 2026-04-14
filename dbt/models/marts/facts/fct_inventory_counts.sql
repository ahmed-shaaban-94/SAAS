{{
    config(
        materialized='incremental',
        unique_key='count_key',
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
            "CREATE INDEX IF NOT EXISTS idx_fct_inv_counts_tenant ON {{ this }} (tenant_id)",
            "CREATE INDEX IF NOT EXISTS idx_fct_inv_counts_product ON {{ this }} (product_key)",
            "CREATE INDEX IF NOT EXISTS idx_fct_inv_counts_site ON {{ this }} (site_key)",
            "CREATE INDEX IF NOT EXISTS idx_fct_inv_counts_date ON {{ this }} (count_date)",
            "CREATE INDEX IF NOT EXISTS idx_fct_inv_counts_loaded_at ON {{ this }} (loaded_at)"
        ]
    )
}}

-- Physical inventory counts fact table
-- Grain: one physical count record per (tenant, drug, site, count_date, batch)
-- Joins to dim_product, dim_site, dim_date for surrogate keys

WITH stg AS (
    SELECT * FROM {{ ref('stg_inventory_counts') }}
    {% if is_incremental() %}
    WHERE loaded_at > (SELECT MAX(loaded_at) FROM {{ this }})
    {% endif %}
),

with_keys AS (
    SELECT
        -- Deterministic surrogate key
        ('x' || LEFT(MD5(
            COALESCE(c.tenant_id::TEXT,  '') || '|' ||
            COALESCE(c.count_date::TEXT, '') || '|' ||
            COALESCE(c.drug_code,        '') || '|' ||
            COALESCE(c.site_code,        '') || '|' ||
            COALESCE(c.batch_number,     '')
        ), 16))::BIT(64)::BIGINT            AS count_key,

        c.tenant_id,
        COALESCE(p.product_key, -1)         AS product_key,
        COALESCE(s.site_key,    -1)         AS site_key,
        COALESCE(dd.date_key,   -1)         AS date_key,
        c.count_date,
        c.batch_number,
        ROUND(c.counted_quantity, 4)        AS counted_quantity,
        c.counted_by,
        c.notes,
        c.loaded_at

    FROM stg c
    LEFT JOIN {{ ref('dim_product') }} p  ON c.drug_code  = p.drug_code  AND c.tenant_id = p.tenant_id
    LEFT JOIN {{ ref('dim_site') }}    s  ON c.site_code  = s.site_code  AND c.tenant_id = s.tenant_id
    LEFT JOIN {{ ref('dim_date') }}    dd ON c.count_date = dd.full_date
)

SELECT * FROM with_keys
