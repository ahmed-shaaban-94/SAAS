{{
    config(
        materialized='table',
        schema='marts'
    )
}}

-- Site/location dimension
-- SCD Type 1: latest attribute wins
-- Includes area_manager (site-level geographic grouping)
-- key = -1 reserved for Unknown/Unassigned

WITH ranked AS (
    SELECT
        site_code,
        site_name,
        area_manager,
        ROW_NUMBER() OVER (
            PARTITION BY site_code
            ORDER BY invoice_date DESC
        ) AS rn
    FROM {{ ref('stg_sales') }}
    WHERE site_code IS NOT NULL
)

SELECT
    ROW_NUMBER() OVER (ORDER BY site_code)::INT            AS site_key,
    site_code,
    site_name,
    area_manager
FROM ranked
WHERE rn = 1

UNION ALL

SELECT
    -1                 AS site_key,
    '__UNKNOWN__'      AS site_code,
    'Unknown'          AS site_name,
    'Unknown'          AS area_manager
