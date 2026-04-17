{{
    config(
        materialized='view',
        schema='bronze'
    )
}}

-- Bronze inventory_counts view: direct reference to the raw bronze.inventory_counts table
-- Data is loaded by the Python bronze loader, not by dbt
-- This model exists so downstream staging/marts models can ref() it

SELECT
    id,
    tenant_id,
    source_file,
    loaded_at,
    count_date,
    drug_code,
    site_code,
    batch_number,
    counted_quantity,
    counted_by,
    notes

FROM {{ source('bronze', 'inventory_counts') }}
