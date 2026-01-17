{{
    config(
        materialized='table',
        schema='marts',
        unique_key='date_key'
    )
}}

WITH date_range AS (
    SELECT 
        generate_series(
            '2023-01-01'::date,
            '2025-12-31'::date,
            '1 day'::interval
        ) as full_date
),

enriched_dates AS (
    SELECT
        TO_CHAR(full_date, 'YYYYMMDD')::integer as date_key,
        full_date,
        EXTRACT(YEAR FROM full_date) as year,
        EXTRACT(QUARTER FROM full_date) as quarter,
        EXTRACT(MONTH FROM full_date) as month,
        TO_CHAR(full_date, 'Month') as month_name,
        EXTRACT(WEEK FROM full_date) as week_of_year,
        EXTRACT(DAY FROM full_date) as day_of_month,
        EXTRACT(DOW FROM full_date) as day_of_week,
        TO_CHAR(full_date, 'Day') as day_name,
        EXTRACT(DOY FROM full_date) as day_of_year,
        CASE 
            WHEN EXTRACT(DOW FROM full_date) IN (0, 6) THEN TRUE
            ELSE FALSE
        END as is_weekend,
        CASE 
            WHEN EXTRACT(MONTH FROM full_date) = 1 AND EXTRACT(DAY FROM full_date) = 1 THEN 'New Year'
            WHEN EXTRACT(MONTH FROM full_date) = 12 AND EXTRACT(DAY FROM full_date) = 25 THEN 'Christmas'
            ELSE 'Regular Day'
        END as holiday_flag
)

SELECT *
FROM enriched_dates