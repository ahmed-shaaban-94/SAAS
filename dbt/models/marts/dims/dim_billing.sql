{{
    config(
        materialized='table',
        schema='marts',
        post_hook=[
            "CREATE INDEX IF NOT EXISTS idx_dim_billing_billing_way ON {{ this }} (billing_way)",
            "CREATE INDEX IF NOT EXISTS idx_dim_billing_billing_key ON {{ this }} (billing_key)"
        ]
    )
}}

-- Billing dimension
-- Groups billing_way into 5 categories and flags return types

WITH billing_types AS (
    SELECT DISTINCT
        billing_way
    FROM {{ ref('stg_sales') }}
    WHERE billing_way IS NOT NULL
),

numbered AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY billing_way)::INT               AS billing_key,
        billing_way,
        CASE
            WHEN billing_way ILIKE '%Delivery Credit%' THEN 'Delivery Credit'
            WHEN billing_way ILIKE '%Delivery%'        THEN 'Delivery'
            WHEN billing_way ILIKE '%Pick-Up%'         THEN 'Pick-Up'
            WHEN billing_way ILIKE '%Credit%'          THEN 'Credit'
            WHEN billing_way ILIKE '%Cash%'            THEN 'Cash'
            ELSE 'Unknown'
        END                                                         AS billing_group,
        billing_way ILIKE '%Return%'                                AS is_return_type
    FROM billing_types
)

SELECT * FROM numbered

UNION ALL

SELECT
    -1              AS billing_key,
    'Unknown'       AS billing_way,
    'Unknown'       AS billing_group,
    FALSE           AS is_return_type
