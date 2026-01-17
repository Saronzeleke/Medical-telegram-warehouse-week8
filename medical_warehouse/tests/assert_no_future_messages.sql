-- Custom test: Ensure no messages have future dates
SELECT 
    message_id,
    message_timestamp
FROM {{ ref('stg_telegram_messages') }}
WHERE message_timestamp > CURRENT_TIMESTAMP + INTERVAL '1 day'