{{
    config(
        materialized='view',
        schema='bronze'
    )
}}

-- Bronze suppliers view: direct reference to the raw bronze.suppliers table
-- Data is loaded by the Python bronze loader, not by dbt
-- This model exists so downstream staging/marts models can ref() it

SELECT
    id,
    tenant_id,
    source_file,
    loaded_at,
    supplier_code,
    supplier_name,
    contact_name,
    contact_phone,
    contact_email,
    address,
    payment_terms_days,
    lead_time_days,
    is_active,
    notes

FROM {{ source('bronze', 'suppliers') }}
