{{
    config(
        materialized='table',
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

-- Silver layer: cleaned sales data
-- Deduplicates, trims text, renames for clarity
-- Cleans NULLs, masked values (#), normalizes drug_status, standardizes billing
--
-- Financial: keeps gross_sales (as sales) + subtotal5_discount (as discount)
-- net_sales deliberately NOT passed to silver — use gross for all KPIs
-- subtotal5_discount is NEGATIVE in the ERP (e.g. -13.2 = EGP 13.2 discount)
--
-- Dropped from bronze (ERP-internal / redundant / net):
--   net_sales, sales_not_tax, paid, dis_tax, tax, add_dis, kzwi1,
--   billing_document, fi_document_no, crm_order, knumv, item_no,
--   mat_group, mat_group_short, cosm_mg, certification, assignment,
--   ref_return_date, ref_return
--
-- Dropped from silver: id (surrogate)

WITH source AS (
    SELECT
        -- Metadata
        id,
        tenant_id,
        source_file,
        source_quarter,
        loaded_at,
        -- Transaction
        reference_no,
        date,
        billing_type,
        billing_type2,
        -- Product
        material,
        material_desc,
        brand,
        item_cluster,
        item_status,
        -- Classification
        category,
        subcategory,
        division,
        segment,
        -- Customer / Site
        customer,
        customer_name,
        site,
        site_name,
        buyer,
        -- Personnel
        personel_number,
        person_name,
        position,
        area_mg,
        -- Financial (gross + discount only; net_sales deliberately not passed to silver)
        quantity,
        gross_sales,
        subtotal5_discount,
        -- Insurance
        insurance_tel,
        insurance_no
    FROM {{ ref('bronze_sales') }}
),

deduplicated AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY tenant_id, reference_no, date, material, customer, site, quantity
            ORDER BY id
        ) AS row_num
    FROM source
)

SELECT
    -- Metadata
    tenant_id,
    source_file,
    source_quarter,
    loaded_at,

    -- Transaction (IDs: keep NULL)
    NULLIF(TRIM(reference_no), '')      AS invoice_id,
    date                                AS invoice_date,
    CASE billing_type
        WHEN 'اجل' THEN 'Credit'
        WHEN 'فورى' THEN 'Cash'
        WHEN 'توصيل' THEN 'Delivery'
        WHEN 'مرتجع توصيل' THEN 'Delivery Return'
        WHEN 'مرتجع اجل' THEN 'Credit Return'
        WHEN 'مرتجع فورى' THEN 'Cash Return'
        WHEN 'Pick-Up Order' THEN 'Pick-Up'
        WHEN 'Pick-Up Order Return' THEN 'Pick-Up Return'
        WHEN 'توصيل - اجل' THEN 'Delivery Credit'
        WHEN 'مرتجع توصيل - اجل' THEN 'Delivery Credit Return'
        ELSE TRIM(billing_type)
    END                                 AS billing_way,
    NULLIF(TRIM(billing_type2), '')     AS billing_id,

    -- Product (codes: keep NULL, names: Unknown)
    NULLIF(TRIM(material), '')          AS drug_code,
    COALESCE(NULLIF(TRIM(material_desc), ''), 'Unknown')  AS drug_name,
    COALESCE(NULLIF(TRIM(brand), ''), 'Unknown')          AS drug_brand,
    COALESCE(NULLIF(TRIM(item_cluster), ''), 'Uncategorized')  AS drug_cluster,

    -- Drug status: normalize variants (strip NBSP + whitespace, unify spelling, extract -T flag)
    -- Note: bronze data contains \u00A0 (non-breaking space) — must strip before matching
    CASE
        WHEN UPPER(REGEXP_REPLACE(REGEXP_REPLACE(item_status, '[\s\u00A0]+', '', 'g'), '[-_]?T$', '')) IN ('ACTIVE')    THEN 'Active'
        WHEN UPPER(REGEXP_REPLACE(REGEXP_REPLACE(item_status, '[\s\u00A0]+', '', 'g'), '[-_]?T$', '')) IN ('CANCELLED', 'CANCELED') THEN 'Cancelled'
        WHEN UPPER(REGEXP_REPLACE(REGEXP_REPLACE(item_status, '[\s\u00A0]+', '', 'g'), '[-_]?T$', '')) IN ('DELISTED')  THEN 'Delisted'
        WHEN UPPER(REGEXP_REPLACE(REGEXP_REPLACE(item_status, '[\s\u00A0]+', '', 'g'), '[-_]?T$', '')) IN ('NEW')       THEN 'New'
        WHEN item_status IS NULL OR TRIM(item_status) = '' THEN 'Unknown'
        ELSE 'Unknown'
    END                                 AS drug_status,
    item_status ~ '[-_\s]T$'           AS is_temporary,

    -- Classification (Uncategorized for NULLs)
    COALESCE(NULLIF(TRIM(category), ''), 'Uncategorized')       AS drug_category,
    COALESCE(NULLIF(TRIM(subcategory), ''), 'Uncategorized')    AS drug_subcategory,
    COALESCE(NULLIF(TRIM(division), ''), 'Uncategorized')       AS drug_division,
    COALESCE(NULLIF(TRIM(segment), ''), 'Uncategorized')        AS drug_segment,

    -- Customer / Site (names: Unknown + # cleanup, IDs: keep NULL)
    NULLIF(TRIM(customer), '')          AS customer_id,
    CASE
        WHEN customer_name IS NULL OR TRIM(customer_name) = '' THEN 'Unknown'
        WHEN customer_name ~ '^[#\s\*\.]+$' THEN 'Unknown'
        WHEN customer_name ~ '#' THEN REGEXP_REPLACE(customer_name, '[#]+', '', 'g')
        ELSE TRIM(customer_name)
    END                                 AS customer_name,
    NULLIF(TRIM(site), '')              AS site_code,
    COALESCE(NULLIF(TRIM(site_name), ''), 'Unknown')      AS site_name,
    COALESCE(NULLIF(TRIM(buyer), ''), 'Unknown')           AS buyer,

    -- Personnel (names: Unknown, IDs: keep NULL)
    NULLIF(TRIM(personel_number), '')   AS staff_id,
    COALESCE(NULLIF(TRIM(person_name), ''), 'Unknown')     AS staff_name,
    COALESCE(NULLIF(TRIM(position), ''), 'Unknown')        AS staff_position,
    COALESCE(NULLIF(TRIM(area_mg), ''), 'Unknown')         AS area_manager,

    -- Financial: gross sales + discount + net amount
    -- NOTE: subtotal5_discount is NEGATIVE in the ERP (e.g. -13.2 means 13.2 discount)
    COALESCE(quantity, 0)               AS quantity,
    COALESCE(gross_sales, 0)            AS sales,
    COALESCE(subtotal5_discount, 0)     AS discount,
    ROUND((COALESCE(gross_sales, 0) + COALESCE(subtotal5_discount, 0))::NUMERIC, 2) AS net_amount,

    -- Derived: date parts (faster grouping in dashboards)
    EXTRACT(YEAR FROM date)::INT        AS invoice_year,
    EXTRACT(MONTH FROM date)::INT       AS invoice_month,
    EXTRACT(QUARTER FROM date)::INT     AS invoice_quarter,

    -- Derived: flags
    CASE
        WHEN billing_type IN ('مرتجع توصيل', 'مرتجع اجل', 'مرتجع فورى',
                              'Pick-Up Order Return', 'مرتجع توصيل - اجل')
        THEN TRUE
        WHEN COALESCE(quantity, 0) < 0 THEN TRUE
        ELSE FALSE
    END                                 AS is_return,
    (insurance_no IS NOT NULL AND TRIM(insurance_no) <> '')  AS has_insurance,
    (NULLIF(TRIM(customer), '') = NULLIF(TRIM(site), ''))    AS is_walk_in,
    (personel_number IS NOT NULL AND TRIM(personel_number) <> '')  AS has_staff,

    -- Insurance (keep NULL — optional fields)
    NULLIF(TRIM(insurance_tel), '')     AS insurance_tel,
    NULLIF(TRIM(insurance_no), '')      AS insurance_no

FROM deduplicated
WHERE row_num = 1
