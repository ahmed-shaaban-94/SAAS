{{
    config(
        materialized='view',
        schema='bronze'
    )
}}

-- Bronze stock_adjustments view: direct reference to the raw bronze.stock_adjustments table
-- Data is loaded by the Python bronze loader, not by dbt
-- This model exists so downstream staging/marts models can ref() it

SELECT
    id,
    tenant_id,
    source_file,
    loaded_at,
    adjustment_date,
    adjustment_type,
    drug_code,
    site_code,
    batch_number,
    quantity,
    reason,
    authorized_by,
    notes

FROM {{ source('bronze', 'stock_adjustments') }}
