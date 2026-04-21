{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert',
        unique_key=['tenant_id', 'invoice_id', 'invoice_date', 'drug_code', 'site_code'],
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

-- Silver layer: POS transactions reshaped to the stg_sales column contract.
-- Source: bronze.pos_transactions (migration 056) — grain is ONE ROW per
--         (tenant_id, transaction_id, drug_code) per the table UNIQUE constraint.
-- Sink:   columns identical to stg_sales so a future `stg_sales_unified`
--         model can UNION ALL the two without casting. Dimensional enrichment
--         (drug_name/brand/category, site_name, staff_name, etc.) is deliberately
--         left as 'Unknown' here and resolved downstream by joins to dim_product /
--         dim_site / dim_staff (gold layer).
--
-- Sign conventions (mirrors stg_sales so UNION math lines up):
--   quantity  — NEGATIVE on returns, POSITIVE on sales.
--   sales     — gross line value, NEGATIVE on returns.
--   discount  — NEGATIVE when a discount was applied (e.g. -13.2 = 13.2 off),
--               0 otherwise. bronze.pos_transactions stores discount as a
--               positive magnitude; we negate here for stg_sales parity.
--   net_amount = sales + discount (so net == sales on a zero-discount sale).
--
-- Flags:
--   is_return    — from bronze.is_return
--   has_insurance — payment_method = 'insurance'
--   is_walk_in   — customer_id IS NULL (no customer scanned at POS)
--   has_staff    — cashier_id IS NOT NULL
--
-- source_quarter / source_file are synthesized so lineage dashboards can
-- tell POS rows apart from ERP rows at a glance.

WITH source AS (
    SELECT
        tenant_id,
        source_type,
        loaded_at,
        transaction_id,
        transaction_date,
        site_code,
        register_id,
        cashier_id,
        customer_id,
        drug_code,
        -- batch_number intentionally NOT in stg_sales shape; the batch dim
        -- is resolved from dim_batch via drug_code + date elsewhere.
        quantity,
        unit_price,
        discount,
        net_amount,
        payment_method,
        insurance_no,
        is_return,
        pharmacist_id
    FROM {{ source('bronze', 'pos_transactions') }}
    {% if is_incremental() %}
    WHERE loaded_at > (SELECT MAX(loaded_at) - INTERVAL '3 days' FROM {{ this }})
    {% endif %}
),

-- bronze.pos_transactions UNIQUEs (tenant_id, transaction_id, drug_code)
-- so duplicates should be impossible, but dbt incremental re-runs can
-- race with bronze inserts. Deduplicate defensively on the same key.
deduplicated AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY tenant_id, transaction_id, drug_code, site_code
            ORDER BY loaded_at DESC
        ) AS row_num
    FROM source
)

SELECT
    -- Metadata
    tenant_id,
    'pos:' || source_type                   AS source_file,
    'POS-' || TO_CHAR(transaction_date, 'YYYY"Q"Q') AS source_quarter,
    loaded_at,

    -- Transaction identifiers
    NULLIF(TRIM(transaction_id), '')        AS invoice_id,
    transaction_date::DATE                  AS invoice_date,
    CASE payment_method
        WHEN 'cash'      THEN 'POS-Cash'
        WHEN 'card'      THEN 'POS-Card'
        WHEN 'insurance' THEN 'POS-Insurance'
        WHEN 'mixed'     THEN 'POS-Mixed'
        ELSE 'POS-Unknown'
    END                                     AS billing_way,
    NULLIF(TRIM(register_id), '')           AS billing_id,

    -- Product (POS bronze carries only drug_code — richer attributes resolve
    -- through dim_product downstream; 'Unknown' keeps the column NOT NULL-friendly)
    NULLIF(TRIM(drug_code), '')             AS drug_code,
    'Unknown'::TEXT                         AS drug_name,
    'Unknown'::TEXT                         AS drug_brand,
    'Uncategorized'::TEXT                   AS drug_cluster,
    'Unknown'::TEXT                         AS drug_status,
    FALSE                                   AS is_temporary,

    -- Classification — deferred to dim_product
    'Uncategorized'::TEXT                   AS drug_category,
    'Uncategorized'::TEXT                   AS drug_subcategory,
    'Uncategorized'::TEXT                   AS drug_division,
    'Uncategorized'::TEXT                   AS drug_segment,

    -- Customer / Site
    NULLIF(TRIM(customer_id), '')           AS customer_id,
    CASE
        WHEN customer_id IS NULL OR TRIM(customer_id) = '' THEN 'Walk-in'
        ELSE 'Unknown'
    END                                     AS customer_name,
    NULLIF(TRIM(site_code), '')             AS site_code,
    'Unknown'::TEXT                         AS site_name,
    'Unknown'::TEXT                         AS buyer,

    -- Personnel — cashier maps to staff_id; POS doesn't track hierarchy,
    -- all POS staff are 'Cashier' until we enrich from an HR dim.
    NULLIF(TRIM(cashier_id), '')            AS staff_id,
    'Unknown'::TEXT                         AS staff_name,
    'Cashier'::TEXT                         AS staff_position,
    'Unknown'::TEXT                         AS area_manager,

    -- Financial — mirror stg_sales sign conventions so UNION math is safe.
    -- quantity: POS bronze may store positive magnitude on returns; flip.
    -- sales:    gross line value = unit_price * signed_quantity
    -- discount: bronze carries positive magnitude; negate for stg_sales parity.
    CASE
        WHEN COALESCE(is_return, FALSE) AND COALESCE(quantity, 0) > 0 THEN -quantity
        ELSE COALESCE(quantity, 0)
    END                                     AS quantity,
    ROUND(
        (COALESCE(unit_price, 0)
         * CASE
               WHEN COALESCE(is_return, FALSE) AND COALESCE(quantity, 0) > 0 THEN -quantity
               ELSE COALESCE(quantity, 0)
           END
        )::NUMERIC, 4
    )                                       AS sales,
    -- Negate to match stg_sales: discount stored negative (so net = sales + discount).
    -(ABS(COALESCE(discount, 0)))           AS discount,
    ROUND(
        (COALESCE(unit_price, 0)
         * CASE
               WHEN COALESCE(is_return, FALSE) AND COALESCE(quantity, 0) > 0 THEN -quantity
               ELSE COALESCE(quantity, 0)
           END
         - ABS(COALESCE(discount, 0))
        )::NUMERIC, 4
    )                                       AS net_amount,

    -- Derived date parts (matches stg_sales)
    EXTRACT(YEAR FROM transaction_date)::INT    AS invoice_year,
    EXTRACT(MONTH FROM transaction_date)::INT   AS invoice_month,
    EXTRACT(QUARTER FROM transaction_date)::INT AS invoice_quarter,

    -- Derived flags
    COALESCE(is_return, FALSE)              AS is_return,
    (payment_method = 'insurance')          AS has_insurance,
    (customer_id IS NULL OR TRIM(customer_id) = '') AS is_walk_in,
    (cashier_id IS NOT NULL AND TRIM(cashier_id) <> '') AS has_staff,

    -- Insurance (POS bronze has no phone; keep NULL for column-shape parity)
    NULL::TEXT                              AS insurance_tel,
    NULLIF(TRIM(insurance_no), '')          AS insurance_no

FROM deduplicated
WHERE row_num = 1
