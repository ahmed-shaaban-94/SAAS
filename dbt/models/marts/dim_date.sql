{{
    config(
        materialized='table',
        schema='marts'
    )
}}

-- Calendar dimension (2023-2025)
-- Egypt weekend: Friday & Saturday
-- month (INT) doubles as month_sort, day_of_week (INT) doubles as day_name sort
-- Includes ISO week number, week_start_date, year_week, quarter_label, year_month

WITH date_spine AS (
    SELECT
        generate_series(
            '2023-01-01'::date,
            '2025-12-31'::date,
            '1 day'::interval
        )::date AS full_date
)

SELECT
    TO_CHAR(full_date, 'YYYYMMDD')::INT          AS date_key,
    full_date,
    EXTRACT(YEAR FROM full_date)::INT             AS year,
    EXTRACT(QUARTER FROM full_date)::INT          AS quarter,
    EXTRACT(MONTH FROM full_date)::INT            AS month,
    TRIM(TO_CHAR(full_date, 'Month'))             AS month_name,
    EXTRACT(ISODOW FROM full_date)::INT           AS day_of_week,
    TRIM(TO_CHAR(full_date, 'Day'))               AS day_name,
    EXTRACT(ISODOW FROM full_date) IN (5, 6)      AS is_weekend,

    -- Week columns
    EXTRACT(WEEK FROM full_date)::INT             AS week_number,
    (full_date - (EXTRACT(ISODOW FROM full_date)::INT - 1) * INTERVAL '1 day')::DATE
                                                  AS week_start_date,
    EXTRACT(YEAR FROM full_date)::INT || '-W' || LPAD(EXTRACT(WEEK FROM full_date)::INT::TEXT, 2, '0')
                                                  AS year_week,

    -- Period labels
    'Q' || EXTRACT(QUARTER FROM full_date)::INT || ' ' || EXTRACT(YEAR FROM full_date)::INT
                                                  AS quarter_label,
    EXTRACT(YEAR FROM full_date)::INT || '-' || LPAD(EXTRACT(MONTH FROM full_date)::INT::TEXT, 2, '0')
                                                  AS year_month

FROM date_spine
ORDER BY full_date
