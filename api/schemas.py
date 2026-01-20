from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from enum import Enum

# Enums
class ImageCategory(str, Enum):
    PROMOTIONAL = "promotional"
    PRODUCT_DISPLAY = "product_display"
    LIFESTYLE = "lifestyle"
    OTHER = "other"

class ChannelType(str, Enum):
    PHARMACEUTICAL = "Pharmaceutical"
    COSMETICS = "Cosmetics"
    MEDICAL = "Medical"

# Base schemas
class BaseResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

# Channel schemas
class ChannelBase(BaseModel):
    channel_name: str
    channel_type: ChannelType
    total_posts: int
    avg_views: float
    activity_level: str

class Channel(ChannelBase):
    channel_key: int
    first_post_date: date
    last_post_date: date
    
    class Config:
        from_attributes = True

# Message schemas
class MessageBase(BaseModel):
    message_id: int
    channel_name: str
    message_date: datetime
    message_preview: str = Field(..., max_length=200)
    view_count: int
    forward_count: int
    has_image: bool

class Message(MessageBase):
    message_text: Optional[str]
    forward_rate: Optional[float]
    time_of_day: Optional[str]
    
    class Config:
        from_attributes = True

# Top Products schemas
class TopProduct(BaseModel):
    product_term: str = Field(..., description="Product name or keyword")
    occurrence_count: int = Field(..., description="Number of times mentioned")
    unique_channels: int = Field(..., description="Number of channels mentioning")
    sample_messages: List[str] = Field(default_factory=list, description="Example messages")
    last_mentioned: Optional[date] = Field(None, description="Most recent mention")
    
    @validator('sample_messages')
    def limit_sample_messages(cls, v):
        return v[:3]  # Limit to 3 sample messages

# Channel Activity schemas
class DailyActivity(BaseModel):
    date: date
    message_count: int
    total_views: int
    avg_views: float
    image_count: int
    image_percentage: float

class ChannelActivity(BaseResponse):
    channel_name: str
    channel_type: ChannelType
    period: str
    start_date: date
    end_date: date
    total_messages: int
    total_views: int
    avg_views_per_message: float
    image_usage_percentage: float
    daily_activity: List[DailyActivity]
    top_categories: Dict[str, int] = Field(..., description="Image category counts")
    engagement_trend: str = Field(..., description="Trend description")

# Search schemas
class SearchMessage(BaseModel):
    message_id: int
    channel_name: str
    message_date: datetime
    message_text: str
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Search relevance score")
    view_count: int
    has_image: bool
    matched_terms: List[str] = Field(default_factory=list, description="Matched search terms")

class MessageSearchResult(BaseResponse):
    query: str
    total_results: int
    limit: int
    offset: int
    has_more: bool
    messages: List[SearchMessage]
    facets: Dict[str, Dict[str, int]] = Field(
        default_factory=dict,
        description="Search facets by channel and date"
    )

# Visual Content schemas
class CategoryStats(BaseModel):
    category: ImageCategory
    count: int
    percentage: float
    avg_confidence: float
    avg_views: Optional[float]
    avg_forwards: Optional[float]

class ChannelVisualStats(BaseModel):
    channel_name: str
    total_images: int
    images_percentage: float
    top_category: ImageCategory
    top_category_percentage: float
    avg_detection_confidence: float

class DateVisualStats(BaseModel):
    date: date
    image_count: int
    promotional_count: int
    product_display_count: int
    avg_confidence: float

class VisualContentStats(BaseResponse):
    group_by: str
    total_images_analyzed: int
    overall_avg_confidence: float
    category_distribution: List[CategoryStats]
    channel_stats: Optional[List[ChannelVisualStats]]
    date_stats: Optional[List[DateVisualStats]]
    insights: List[str] = Field(default_factory=list, description="Key insights")

# Engagement Trend schemas
class EngagementTrend(BaseModel):
    time_period: str
    message_count: int
    metric_value: float
    percentage_change: Optional[float]

# Image Detection schemas
class ImageDetection(BaseModel):
    detection_id: int
    message_id: int
    image_category: ImageCategory
    confidence_score: float
    detected_classes: List[str]
    content_strategy: str
    
    class Config:
        from_attributes = True