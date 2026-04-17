{{
    config(
        materialized='view',
        schema='bronze'
    )
}}

-- Bronze po_lines view: direct reference to the raw bronze.po_lines table
-- Data is loaded by the Python bronze loader, not by dbt
-- This model exists so downstream staging/marts models can ref() it

SELECT
    id,
    tenant_id,
    loaded_at,
    po_number,
    line_number,
    drug_code,
    ordered_quantity,
    unit_price,
    received_quantity,
    line_total

FROM {{ source('bronze', 'po_lines') }}
