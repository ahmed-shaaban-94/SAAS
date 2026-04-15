{{
    config(
        materialized='incremental',
        unique_key='movement_key',
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
            "CREATE INDEX IF NOT EXISTS idx_fct_stock_movements_tenant ON {{ this }} (tenant_id)",
            "CREATE INDEX IF NOT EXISTS idx_fct_stock_movements_product ON {{ this }} (product_key)",
            "CREATE INDEX IF NOT EXISTS idx_fct_stock_movements_site ON {{ this }} (site_key)",
            "CREATE INDEX IF NOT EXISTS idx_fct_stock_movements_date ON {{ this }} (movement_date)",
            "CREATE INDEX IF NOT EXISTS idx_fct_stock_movements_type ON {{ this }} (movement_type)",
            "CREATE INDEX IF NOT EXISTS idx_fct_stock_movements_loaded_at ON {{ this }} (loaded_at)"
        ]
    )
}}

-- Stock movements fact table
-- Grain: one movement event (receipt, adjustment, dispense, return)
-- UNION of 4 sources into a single event stream
-- Surrogate key: MD5 of natural key (deterministic, 64-bit)

WITH receipts AS (
    SELECT
        tenant_id,
        receipt_date                        AS movement_date,
        drug_code,
        site_code,
        batch_number,
        'receipt'                           AS movement_type,
        quantity,                           -- positive (incoming)
        unit_cost,
        receipt_reference                   AS reference,
        loaded_at
    FROM {{ ref('stg_stock_receipts') }}
),

adjustments AS (
    SELECT
        tenant_id,
        adjustment_date                     AS movement_date,
        drug_code,
        site_code,
        batch_number,
        adjustment_type                     AS movement_type,
        quantity,                           -- positive or negative
        NULL::NUMERIC(18,4)                 AS unit_cost,
        reason                              AS reference,
        loaded_at
    FROM {{ ref('stg_stock_adjustments') }}
),

dispenses AS (
    -- Outflow from sales (existing fct_sales — forward-looking FK resolution)
    SELECT
        f.tenant_id,
        d.full_date                         AS movement_date,
        p.drug_code,
        s.site_code,
        NULL                                AS batch_number,
        'dispense'                          AS movement_type,
        -f.quantity,                        -- negative (outgoing)
        NULL::NUMERIC(18,4)                 AS unit_cost,
        f.invoice_id                        AS reference,
        f.loaded_at
    FROM {{ ref('fct_sales') }} f
    INNER JOIN {{ ref('dim_date') }}    d  ON f.date_key    = d.date_key
    INNER JOIN {{ ref('dim_product') }} p  ON f.product_key = p.product_key AND f.tenant_id = p.tenant_id
    INNER JOIN {{ ref('dim_site') }}    s  ON f.site_key    = s.site_key    AND f.tenant_id = s.tenant_id
    WHERE f.quantity > 0
      AND f.is_return = FALSE
),

returns AS (
    -- Inflow from returns (fct_sales rows with is_return = TRUE)
    SELECT
        f.tenant_id,
        d.full_date                         AS movement_date,
        p.drug_code,
        s.site_code,
        NULL                                AS batch_number,
        'return'                            AS movement_type,
        ABS(f.quantity),                    -- positive (incoming)
        NULL::NUMERIC(18,4)                 AS unit_cost,
        f.invoice_id                        AS reference,
        f.loaded_at
    FROM {{ ref('fct_sales') }} f
    INNER JOIN {{ ref('dim_date') }}    d  ON f.date_key    = d.date_key
    INNER JOIN {{ ref('dim_product') }} p  ON f.product_key = p.product_key AND f.tenant_id = p.tenant_id
    INNER JOIN {{ ref('dim_site') }}    s  ON f.site_key    = s.site_key    AND f.tenant_id = s.tenant_id
    WHERE f.is_return = TRUE
),

all_movements AS (
    SELECT * FROM receipts
    UNION ALL
    SELECT * FROM adjustments
    UNION ALL
    SELECT * FROM dispenses
    UNION ALL
    SELECT * FROM returns
),

with_keys AS (
    SELECT
        -- Deterministic surrogate key (MD5 of natural key)
        ('x' || LEFT(MD5(
            COALESCE(m.tenant_id::TEXT,      '') || '|' ||
            COALESCE(m.movement_date::TEXT,  '') || '|' ||
            COALESCE(m.drug_code,            '') || '|' ||
            COALESCE(m.site_code,            '') || '|' ||
            COALESCE(m.movement_type,        '') || '|' ||
            COALESCE(m.reference,            '') || '|' ||
            COALESCE(m.batch_number,         '') || '|' ||
            COALESCE(m.quantity::TEXT,       '')
        ), 16))::BIT(64)::BIGINT            AS movement_key,

        m.tenant_id,
        COALESCE(p.product_key, -1)         AS product_key,
        COALESCE(s.site_key,    -1)         AS site_key,
        COALESCE(dd.date_key,   -1)         AS date_key,
        m.movement_date,
        m.movement_type,
        m.batch_number,
        ROUND(m.quantity, 4)                AS quantity,
        ROUND(m.unit_cost, 4)               AS unit_cost,
        m.reference,
        m.loaded_at

    FROM all_movements m
    LEFT JOIN {{ ref('dim_product') }} p  ON m.drug_code      = p.drug_code  AND m.tenant_id = p.tenant_id
    LEFT JOIN {{ ref('dim_site') }}    s  ON m.site_code       = s.site_code  AND m.tenant_id = s.tenant_id
    LEFT JOIN {{ ref('dim_date') }}    dd ON m.movement_date   = dd.full_date

    {% if is_incremental() %}
    WHERE m.loaded_at > (SELECT MAX(loaded_at) FROM {{ this }})
    {% endif %}
)

SELECT * FROM with_keys
