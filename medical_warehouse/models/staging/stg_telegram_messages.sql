{{
    config(
        materialized='view',
        schema='staging'
    )
}}

WITH raw_data AS (
    SELECT
        message_id,
        channel_name,
        CAST(message_date AS TIMESTAMP) as message_timestamp,
        CAST(message_date AS DATE) as message_date,
        COALESCE(message_text, '') as message_text,
        COALESCE(has_media, FALSE) as has_media,
        image_path,
        COALESCE(views, 0) as views,
        COALESCE(forwards, 0) as forwards,
        raw_data,
        loaded_at
    FROM raw.telegram_messages
    WHERE message_id IS NOT NULL
      AND channel_name IS NOT NULL
      AND message_date IS NOT NULL
),

cleaned_data AS (
    SELECT
        message_id,
        channel_name,
        message_timestamp,
        message_date,
        -- Clean text: remove extra whitespace
        REGEXP_REPLACE(message_text, '\s+', ' ') as message_text,
        LENGTH(COALESCE(message_text, '')) as message_length,
        has_media,
        image_path,
        views,
        forwards,
        -- Flag for images
        CASE 
            WHEN image_path IS NOT NULL AND has_media = TRUE THEN TRUE
            ELSE FALSE
        END as has_image,
        raw_data,
        loaded_at,
        -- Channel type classification
        CASE 
            WHEN LOWER(channel_name) LIKE '%pharma%' THEN 'Pharmaceutical'
            WHEN LOWER(channel_name) LIKE '%cosmetic%' THEN 'Cosmetics'
            ELSE 'Medical'
        END as channel_type
    FROM raw_data
)

SELECT
    ROW_NUMBER() OVER (ORDER BY message_timestamp) as staging_id,
    *
FROM cleaned_data