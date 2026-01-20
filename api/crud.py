from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc, and_, or_, text, case, literal_column
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
import re
from collections import Counter

from . import models, schemas

# Medical product keywords for extraction
MEDICAL_KEYWORDS = {
    'pain_relief': ['paracetamol', 'ibuprofen', 'aspirin', 'diclofenac', 'naproxen'],
    'antibiotics': ['amoxicillin', 'azithromycin', 'ciprofloxacin', 'doxycycline'],
    'vitamins': ['vitamin c', 'vitamin d', 'multivitamin', 'b complex'],
    'chronic': ['insulin', 'metformin', 'atenolol', 'losartan'],
    'cosmetics': ['cream', 'lotion', 'serum', 'moisturizer', 'shampoo'],
    'equipment': ['thermometer', 'mask', 'gloves', 'syringe', 'bandage']
}

async def get_top_products(db: Session, limit: int = 10, days: int = 30,
                          channel_name: Optional[str] = None,
                          min_occurrences: int = 2) -> List[schemas.TopProduct]:
    """Extract most frequently mentioned medical products"""
    
    # Calculate date threshold
    threshold_date = datetime.now() - timedelta(days=days)
    
    # Build query
    query = db.query(models.Message).filter(
        models.Message.message_text.isnot(None),
        models.Message.loaded_at >= threshold_date
    )
    
    if channel_name:
        query = query.join(models.Channel).filter(
            models.Channel.channel_name == channel_name
        )
    
    messages = query.limit(1000).all()  # Sample for performance
    
    # Extract product mentions
    product_counter = Counter()
    channel_mentions = {}
    message_examples = {}
    last_mentions = {}
    
    for msg in messages:
        text_lower = msg.message_text.lower()
        
        # Check each keyword category
        for category, keywords in MEDICAL_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    product_counter[keyword] += 1
                    
                    # Track channel mentions
                    if keyword not in channel_mentions:
                        channel_mentions[keyword] = set()
                    channel_mentions[keyword].add(msg.channel.channel_name if msg.channel else 'unknown')
                    
                    # Track message examples
                    if keyword not in message_examples:
                        message_examples[keyword] = []
                    if len(message_examples[keyword]) < 3:
                        # Extract context around keyword
                        start = max(0, text_lower.find(keyword) - 50)
                        end = min(len(text_lower), text_lower.find(keyword) + len(keyword) + 50)
                        context = msg.message_text[start:end]
                        if context:
                            message_examples[keyword].append(context)
                    
                    # Track last mention
                    msg_date = msg.date.full_date if msg.date else None
                    if msg_date:
                        current_last = last_mentions.get(keyword)
                        if not current_last or msg_date > current_last:
                            last_mentions[keyword] = msg_date
    
    # Convert to response format
    results = []
    for product, count in product_counter.most_common(limit):
        if count >= min_occurrences:
            results.append(schemas.TopProduct(
                product_term=product.title(),
                occurrence_count=count,
                unique_channels=len(channel_mentions.get(product, set())),
                sample_messages=message_examples.get(product, [])[:3],
                last_mentioned=last_mentions.get(product)
            ))
    
    return results

async def get_channel_activity(db: Session, channel_name: str, 
                              period: str = "7d") -> schemas.ChannelActivity:
    """Get channel activity for specified period"""
    
    # Map period to days
    period_days = {
        "1d": 1, "7d": 7, "30d": 30, "90d": 90
    }
    days = period_days.get(period, 7)
    start_date = date.today() - timedelta(days=days)
    
    # Get channel info
    channel = db.query(models.Channel).filter(
        models.Channel.channel_name == channel_name
    ).first()
    
    if not channel:
        raise ValueError(f"Channel '{channel_name}' not found")
    
    # Get messages in period
    messages_query = db.query(models.Message).join(models.DateDim).filter(
        models.Message.channel_key == channel.channel_key,
        models.DateDim.full_date >= start_date
    )
    
    messages = messages_query.all()
    
    if not messages:
        raise ValueError(f"No activity found for channel '{channel_name}' in the last {days} days")
    
    # Get image detections
    images_query = db.query(models.ImageDetection).filter(
        models.ImageDetection.channel_key == channel.channel_key,
        models.ImageDetection.processed_at >= start_date
    )
    
    images = images_query.all()
    
    # Calculate daily activity
    daily_stats = {}
    for msg in messages:
        msg_date = msg.date.full_date
        if msg_date not in daily_stats:
            daily_stats[msg_date] = {
                'message_count': 0,
                'total_views': 0,
                'image_count': 0
            }
        
        daily_stats[msg_date]['message_count'] += 1
        daily_stats[msg_date]['total_views'] += msg.view_count or 0
        
        if msg.has_image:
            daily_stats[msg_date]['image_count'] += 1
    
    # Convert to list format
    daily_activity = []
    for day, stats in sorted(daily_stats.items()):
        msg_count = stats['message_count']
        daily_activity.append(schemas.DailyActivity(
            date=day,
            message_count=msg_count,
            total_views=stats['total_views'],
            avg_views=stats['total_views'] / msg_count if msg_count > 0 else 0,
            image_count=stats['image_count'],
            image_percentage=(stats['image_count'] / msg_count * 100) if msg_count > 0 else 0
        ))
    
    # Calculate image categories
    category_counts = {}
    for img in images:
        category = img.image_category or 'unknown'
        category_counts[category] = category_counts.get(category, 0) + 1
    
    # Calculate engagement trend
    if len(daily_activity) >= 2:
        recent_avg = daily_activity[-1].avg_views
        previous_avg = daily_activity[-2].avg_views if len(daily_activity) >= 2 else recent_avg
        if recent_avg > previous_avg * 1.1:
            trend = "increasing"
        elif recent_avg < previous_avg * 0.9:
            trend = "decreasing"
        else:
            trend = "stable"
    else:
        trend = "insufficient data"
    
    return schemas.ChannelActivity(
        channel_name=channel.channel_name,
        channel_type=schemas.ChannelType(channel.channel_type),
        period=period,
        start_date=start_date,
        end_date=date.today(),
        total_messages=len(messages),
        total_views=sum(m.view_count or 0 for m in messages),
        avg_views_per_message=sum(m.view_count or 0 for m in messages) / len(messages) if messages else 0,
        image_usage_percentage=sum(1 for m in messages if m.has_image) / len(messages) * 100 if messages else 0,
        daily_activity=daily_activity,
        top_categories=category_counts,
        engagement_trend=trend
    )

async def search_messages(db: Session, query: str, limit: int = 20,
                         offset: int = 0, **filters) -> schemas.MessageSearchResult:
    """Search messages with filters and relevance scoring"""
    
    # Build base query
    base_query = db.query(models.Message).join(models.Channel).join(models.DateDim)
    
    # Apply filters
    conditions = []
    
    if filters.get('channel_name'):
        conditions.append(models.Channel.channel_name == filters['channel_name'])
    
    if filters.get('start_date'):
        conditions.append(models.DateDim.full_date >= filters['start_date'])
    
    if filters.get('end_date'):
        conditions.append(models.DateDim.full_date <= filters['end_date'])
    
    if filters.get('has_image') is not None:
        conditions.append(models.Message.has_image == filters['has_image'])
    
    if filters.get('min_views'):
        conditions.append(models.Message.view_count >= filters['min_views'])
    
    if conditions:
        base_query = base_query.filter(and_(*conditions))
    
    # Get total count
    total_results = base_query.count()
    
    # Get messages
    messages = base_query.order_by(desc(models.Message.message_date)).offset(offset).limit(limit).all()
    
    # Calculate relevance scores
    search_terms = [term.lower().strip() for term in query.split() if len(term) >= 2]
    search_results = []
    
    for msg in messages:
        text_lower = (msg.message_text or "").lower()
        channel_lower = (msg.channel.channel_name or "").lower()
        
        # Calculate relevance score
        term_matches = []
        score = 0.0
        
        for term in search_terms:
            if term in text_lower:
                # Count occurrences
                occurrences = text_lower.count(term)
                term_matches.append(term)
                score += occurrences * 0.5
                
                # Boost if in channel name
                if term in channel_lower:
                    score += 1.0
        
        # Normalize score
        if search_terms:
            score = min(1.0, score / len(search_terms))
        
        if term_matches or not search_terms:  # Include all if no search terms
            search_results.append(schemas.SearchMessage(
                message_id=msg.message_id,
                channel_name=msg.channel.channel_name,
                message_date=msg.date.full_date,
                message_text=msg.message_text[:500] + "..." if msg.message_text and len(msg.message_text) > 500 else msg.message_text,
                relevance_score=score,
                view_count=msg.view_count or 0,
                has_image=msg.has_image or False,
                matched_terms=term_matches
            ))
    
    # Sort by relevance if searching
    if search_terms:
        search_results.sort(key=lambda x: x.relevance_score, reverse=True)
    
    # Calculate facets
    facets = {
        'channel': {},
        'date': {}
    }
    
    for msg in messages[:100]:  # Sample for facets
        channel = msg.channel.channel_name
        date_str = str(msg.date.full_date)
        
        facets['channel'][channel] = facets['channel'].get(channel, 0) + 1
        facets['date'][date_str] = facets['date'].get(date_str, 0) + 1
    
    return schemas.MessageSearchResult(
        query=query,
        total_results=total_results,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total_results,
        messages=search_results[:limit],
        facets=facets
    )

async def get_visual_content_stats(db: Session, group_by: str = "channel",
                                  start_date: Optional[date] = None,
                                  end_date: Optional[date] = None,
                                  min_confidence: float = 0.3) -> schemas.VisualContentStats:
    """Get statistics about visual content analysis"""
    
    # Build base query
    query = db.query(models.ImageDetection).join(models.Channel).join(models.DateDim).filter(
        models.ImageDetection.confidence_score >= min_confidence
    )
    
    if start_date:
        query = query.filter(models.DateDim.full_date >= start_date)
    
    if end_date:
        query = query.filter(models.DateDim.full_date <= end_date)
    
    detections = query.all()
    
    if not detections:
        return schemas.VisualContentStats(
            group_by=group_by,
            total_images_analyzed=0,
            overall_avg_confidence=0.0,
            category_distribution=[],
            insights=["No image detections found with specified filters"]
        )
    
    # Calculate overall stats
    total_images = len(detections)
    overall_confidence = sum(d.confidence_score or 0 for d in detections) / total_images
    
    # Calculate category distribution
    category_data = {}
    for det in detections:
        category = det.image_category or 'unknown'
        if category not in category_data:
            category_data[category] = {
                'count': 0,
                'confidence_sum': 0,
                'message_ids': set()
            }
        
        category_data[category]['count'] += 1
        category_data[category]['confidence_sum'] += det.confidence_score or 0
        category_data[category]['message_ids'].add(det.message_id)
    
    category_stats = []
    for category, data in category_data.items():
        # Get engagement for this category
        cat_messages = db.query(models.Message).filter(
            models.Message.message_id.in_(list(data['message_ids']))
        ).all()
        
        avg_views = sum(m.view_count or 0 for m in cat_messages) / len(cat_messages) if cat_messages else None
        avg_forwards = sum(m.forward_count or 0 for m in cat_messages) / len(cat_messages) if cat_messages else None
        
        category_stats.append(schemas.CategoryStats(
            category=schemas.ImageCategory(category) if category in [c.value for c in schemas.ImageCategory] else schemas.ImageCategory.OTHER,
            count=data['count'],
            percentage=(data['count'] / total_images) * 100,
            avg_confidence=data['confidence_sum'] / data['count'],
            avg_views=avg_views,
            avg_forwards=avg_forwards
        ))
    
    # Group-specific stats
    channel_stats = None
    date_stats = None
    
    if group_by == "channel":
        channel_data = {}
        for det in detections:
            channel = det.channel.channel_name
            if channel not in channel_data:
                channel_data[channel] = {
                    'total': 0,
                    'categories': {},
                    'confidence_sum': 0
                }
            
            channel_data[channel]['total'] += 1
            channel_data[channel]['confidence_sum'] += det.confidence_score or 0
            
            category = det.image_category or 'unknown'
            channel_data[channel]['categories'][category] = channel_data[channel]['categories'].get(category, 0) + 1
        
        channel_stats = []
        for channel, data in channel_data.items():
            top_category = max(data['categories'].items(), key=lambda x: x[1])[0] if data['categories'] else 'unknown'
            
            channel_stats.append(schemas.ChannelVisualStats(
                channel_name=channel,
                total_images=data['total'],
                images_percentage=(data['total'] / total_images) * 100,
                top_category=schemas.ImageCategory(top_category) if top_category in [c.value for c in schemas.ImageCategory] else schemas.ImageCategory.OTHER,
                top_category_percentage=(data['categories'].get(top_category, 0) / data['total']) * 100,
                avg_detection_confidence=data['confidence_sum'] / data['total']
            ))
    
    elif group_by == "date":
        date_data = {}
        for det in detections:
            det_date = det.date.full_date
            if det_date not in date_data:
                date_data[det_date] = {
                    'total': 0,
                    'promotional': 0,
                    'product_display': 0,
                    'confidence_sum': 0
                }
            
            date_data[det_date]['total'] += 1
            date_data[det_date]['confidence_sum'] += det.confidence_score or 0
            
            if det.image_category == 'promotional':
                date_data[det_date]['promotional'] += 1
            elif det.image_category == 'product_display':
                date_data[det_date]['product_display'] += 1
        
        date_stats = []
        for det_date, data in sorted(date_data.items()):
            date_stats.append(schemas.DateVisualStats(
                date=det_date,
                image_count=data['total'],
                promotional_count=data['promotional'],
                product_display_count=data['product_display'],
                avg_confidence=data['confidence_sum'] / data['total']
            ))
    
    # Generate insights
    insights = []
    
    # Find best performing category
    if category_stats:
        best_category = max(category_stats, key=lambda x: x.avg_views or 0)
        if best_category.avg_views:
            insights.append(
                f"'{best_category.category.value}' images receive highest engagement "
                f"({best_category.avg_views:.0f} avg views)"
            )
    
    # Check confidence levels
    high_confidence = [d for d in detections if d.confidence_score and d.confidence_score > 0.7]
    if high_confidence:
        insights.append(
            f"{len(high_confidence)} images ({len(high_confidence)/total_images*100:.1f}%) "
            f"have high detection confidence (>70%)"
        )
    
    return schemas.VisualContentStats(
        group_by=group_by,
        total_images_analyzed=total_images,
        overall_avg_confidence=overall_confidence,
        category_distribution=category_stats,
        channel_stats=channel_stats,
        date_stats=date_stats,
        insights=insights
    )