{{
    config(
        materialized='table',
        schema='marts',
        unique_key='channel_key'
    )
}}

WITH channel_stats AS (
    SELECT
        channel_name,
        channel_type,
        MIN(message_date) as first_post_date,
        MAX(message_date) as last_post_date,
        COUNT(*) as total_posts,
        AVG(views) as avg_views,
        SUM(views) as total_views,
        AVG(forwards) as avg_forwards,
        SUM(forwards) as total_forwards
    FROM {{ ref('stg_telegram_messages') }}
    GROUP BY 1, 2
),

channel_activity AS (
    SELECT
        channel_name,
        COUNT(DISTINCT message_date) as active_days,
        AVG(message_length) as avg_message_length,
        SUM(CASE WHEN has_image THEN 1 ELSE 0 END) as total_images
    FROM {{ ref('stg_telegram_messages') }}
    GROUP BY 1
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['cs.channel_name']) }} as channel_key,
    cs.channel_name,
    cs.channel_type,
    cs.first_post_date,
    cs.last_post_date,
    cs.total_posts,
    cs.avg_views,
    cs.total_views,
    cs.avg_forwards,
    cs.total_forwards,
    ca.active_days,
    ca.avg_message_length,
    ca.total_images,
    -- Activity level classification
    CASE 
        WHEN cs.total_posts > 1000 THEN 'High Activity'
        WHEN cs.total_posts > 100 THEN 'Medium Activity'
        ELSE 'Low Activity'
    END as activity_level,
    CURRENT_TIMESTAMP as loaded_at
FROM channel_stats cs
LEFT JOIN channel_activity ca ON cs.channel_name = ca.channel_name