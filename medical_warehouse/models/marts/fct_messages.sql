{{
    config(
        materialized='table',
        schema='marts',
        unique_key='message_id'
    )
}}

SELECT
    stg.message_id,
    dc.channel_key,
    dd.date_key,
    stg.message_text,
    stg.message_length,
    stg.views as view_count,
    stg.forwards as forward_count,
    stg.has_image,
    stg.has_media,
    stg.image_path,
    stg.message_timestamp,
    -- Engagement metrics
    CASE 
        WHEN stg.views > 0 THEN ROUND(stg.forwards::decimal / stg.views * 100, 2)
        ELSE 0
    END as forward_rate,
    -- Time-based attributes
    EXTRACT(HOUR FROM stg.message_timestamp) as hour_of_day,
    CASE 
        WHEN EXTRACT(HOUR FROM stg.message_timestamp) BETWEEN 6 AND 12 THEN 'Morning'
        WHEN EXTRACT(HOUR FROM stg.message_timestamp) BETWEEN 13 AND 18 THEN 'Afternoon'
        WHEN EXTRACT(HOUR FROM stg.message_timestamp) BETWEEN 19 AND 23 THEN 'Evening'
        ELSE 'Night'
    END as time_of_day,
    CURRENT_TIMESTAMP as loaded_at
FROM {{ ref('stg_telegram_messages') }} stg
LEFT JOIN {{ ref('dim_channels') }} dc ON stg.channel_name = dc.channel_name
LEFT JOIN {{ ref('dim_dates') }} dd ON stg.message_date = dd.full_date