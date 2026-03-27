{{
    config(
        materialized='table',
        schema='marts'
    )
}}

-- Staff/personnel dimension
-- SCD Type 1: latest attribute wins
-- key = -1 reserved for Unknown/Unassigned

WITH ranked AS (
    SELECT
        staff_id,
        staff_name,
        staff_position,
        ROW_NUMBER() OVER (
            PARTITION BY staff_id
            ORDER BY invoice_date DESC
        ) AS rn
    FROM {{ ref('stg_sales') }}
    WHERE staff_id IS NOT NULL
)

SELECT
    ROW_NUMBER() OVER (ORDER BY staff_id)::INT            AS staff_key,
    staff_id,
    staff_name,
    staff_position
FROM ranked
WHERE rn = 1

UNION ALL

SELECT
    -1                 AS staff_key,
    '__UNKNOWN__'      AS staff_id,
    'Unknown'          AS staff_name,
    'Unknown'          AS staff_position
