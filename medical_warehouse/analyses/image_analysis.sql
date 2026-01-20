-- Analysis: Do promotional posts get more views?
SELECT 
    fid.image_category,
    COUNT(DISTINCT fid.message_id) as image_count,
    AVG(fm.view_count) as avg_views,
    AVG(fm.forward_count) as avg_forwards,
    AVG(fm.forward_rate) as avg_forward_rate,
    AVG(fid.confidence_score) as avg_confidence
FROM marts.fct_image_detections fid
JOIN marts.fct_messages fm ON fid.message_id = fm.message_id
GROUP BY fid.image_category
ORDER BY avg_views DESC;

-- Analysis: Which channels use more visual content?
SELECT 
    dc.channel_name,
    dc.channel_type,
    COUNT(DISTINCT fm.message_id) as total_messages,
    COUNT(DISTINCT fid.message_id) as messages_with_images,
    ROUND(COUNT(DISTINCT fid.message_id) * 100.0 / COUNT(DISTINCT fm.message_id), 2) as image_percentage,
    AVG(fid.confidence_score) as avg_detection_confidence,
    MODE() WITHIN GROUP (ORDER BY fid.image_category) as most_common_category
FROM marts.dim_channels dc
LEFT JOIN marts.fct_messages fm ON dc.channel_key = fm.channel_key
LEFT JOIN marts.fct_image_detections fid ON fm.message_id = fid.message_id
GROUP BY dc.channel_key, dc.channel_name, dc.channel_type
ORDER BY image_percentage DESC;