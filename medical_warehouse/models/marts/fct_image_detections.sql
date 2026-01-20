{{
    config(
        materialized='table',
        schema='marts',
        unique_key='detection_id'
    )
}}

WITH raw_detections AS (
    SELECT
        message_id,
        channel_name,
        image_path,
        detection_count,
        detected_classes,
        image_category,
        confidence_score,
        has_person,
        has_product,
        processed_at
    FROM raw.yolo_detections
    WHERE message_id IS NOT NULL
),

enriched_detections AS (
    SELECT
        {{ dbt_utils.generate_surrogate_key(['rd.message_id', 'rd.processed_at']) }} as detection_id,
        rd.message_id,
        COALESCE(dc.channel_key, -1) as channel_key,
        COALESCE(dd.date_key, -1) as date_key,
        rd.image_path,
        rd.detection_count,
        rd.detected_classes,
        rd.image_category,
        rd.confidence_score,
        rd.has_person,
        rd.has_product,
        rd.processed_at,
        -- Additional business logic
        CASE 
            WHEN rd.image_category = 'promotional' THEN 'High Engagement Potential'
            WHEN rd.image_category = 'product_display' THEN 'Direct Product Marketing'
            WHEN rd.image_category = 'lifestyle' THEN 'Brand Building'
            ELSE 'Generic Content'
        END as content_strategy,
        -- Quality flags
        CASE 
            WHEN rd.confidence_score > 0.7 THEN 'High Confidence'
            WHEN rd.confidence_score > 0.4 THEN 'Medium Confidence'
            ELSE 'Low Confidence'
        END as confidence_level,
        CURRENT_TIMESTAMP as loaded_at
    FROM raw_detections rd
    LEFT JOIN {{ ref('fct_messages') }} fm ON rd.message_id = fm.message_id
    LEFT JOIN {{ ref('dim_channels') }} dc ON fm.channel_key = dc.channel_key
    LEFT JOIN {{ ref('dim_dates') }} dd ON fm.date_key = dd.date_key
    WHERE rd.detection_count > 0  
)

SELECT *
FROM enriched_detections