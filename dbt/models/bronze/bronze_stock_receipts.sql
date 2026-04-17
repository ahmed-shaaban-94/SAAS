{{
    config(
        materialized='view',
        schema='bronze'
    )
}}

-- Bronze stock_receipts view: direct reference to the raw bronze.stock_receipts table
-- Data is loaded by the Python bronze loader, not by dbt
-- This model exists so downstream staging/marts models can ref() it

SELECT
    id,
    tenant_id,
    source_file,
    loaded_at,
    receipt_date,
    receipt_reference,
    drug_code,
    site_code,
    batch_number,
    expiry_date,
    quantity,
    unit_cost,
    supplier_code,
    po_reference,
    notes

FROM {{ source('bronze', 'stock_receipts') }}
