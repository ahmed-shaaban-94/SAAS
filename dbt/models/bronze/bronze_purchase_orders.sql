{{
    config(
        materialized='view',
        schema='bronze'
    )
}}

-- Bronze purchase_orders view: direct reference to the raw bronze.purchase_orders table
-- Data is loaded by the Python bronze loader, not by dbt
-- This model exists so downstream staging/marts models can ref() it

SELECT
    id,
    tenant_id,
    source_file,
    loaded_at,
    po_number,
    po_date,
    supplier_code,
    site_code,
    status,
    expected_date,
    total_amount,
    notes,
    created_by

FROM {{ source('bronze', 'purchase_orders') }}
