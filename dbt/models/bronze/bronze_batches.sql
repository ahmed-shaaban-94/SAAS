{{
    config(
        materialized='view',
        schema='bronze'
    )
}}

-- Bronze batches view: direct reference to the raw bronze.batches table
-- Data is loaded by the Python bronze loader, not by dbt
-- This model exists so downstream staging/marts models can ref() it

SELECT
    id,
    tenant_id,
    source_file,
    loaded_at,
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
    write_off_reason

FROM {{ source('bronze', 'batches') }}
