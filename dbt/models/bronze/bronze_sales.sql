{{
    config(
        materialized='view',
        schema='bronze'
    )
}}

-- Bronze sales view: direct reference to the raw bronze.sales table
-- Data is loaded by the Python bronze loader, not by dbt
-- This model exists so downstream staging/marts models can ref() it

SELECT
    id,
    source_file,
    source_quarter,
    loaded_at,

    -- Transaction
    reference_no,
    date,
    billing_document,
    billing_type,
    billing_type2,

    -- Product
    material,
    material_desc,
    brand,
    item_cluster,
    item_status,
    category,
    subcategory,
    division,
    segment,
    mat_group,
    mat_group_short,
    cosm_mg,

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

    -- Financials
    quantity,
    net_sales,
    gross_sales,
    sales_not_tax,
    dis_tax,
    tax,
    paid,
    kzwi1,
    subtotal5_discount,
    add_dis

FROM {{ source('bronze', 'sales') }}
