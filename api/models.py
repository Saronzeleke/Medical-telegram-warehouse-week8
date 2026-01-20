from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text, Date, ForeignKey
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class Channel(Base):
    __tablename__ = "dim_channels"
    __table_args__ = {'schema': 'marts'}
    
    channel_key = Column(Integer, primary_key=True)
    channel_name = Column(String(255), nullable=False, index=True)
    channel_type = Column(String(50), nullable=False)
    first_post_date = Column(Date)
    last_post_date = Column(Date)
    total_posts = Column(Integer)
    avg_views = Column(Float)
    activity_level = Column(String(50))
    loaded_at = Column(DateTime, default=func.now())

class DateDim(Base):
    __tablename__ = "dim_dates"
    __table_args__ = {'schema': 'marts'}
    
    date_key = Column(Integer, primary_key=True)
    full_date = Column(Date, nullable=False, unique=True, index=True)
    year = Column(Integer)
    quarter = Column(Integer)
    month = Column(Integer)
    month_name = Column(String(20))
    week_of_year = Column(Integer)
    day_of_week = Column(Integer)
    day_name = Column(String(20))
    is_weekend = Column(Boolean)

class Message(Base):
    __tablename__ = "fct_messages"
    __table_args__ = {'schema': 'marts'}
    
    message_id = Column(Integer, primary_key=True)
    channel_key = Column(Integer, ForeignKey('marts.dim_channels.channel_key'), index=True)
    date_key = Column(Integer, ForeignKey('marts.dim_dates.date_key'), index=True)
    message_text = Column(Text)
    message_length = Column(Integer)
    view_count = Column(Integer)
    forward_count = Column(Integer)
    has_image = Column(Boolean)
    forward_rate = Column(Float)
    hour_of_day = Column(Integer)
    time_of_day = Column(String(20))
    loaded_at = Column(DateTime, default=func.now())
    
    channel = relationship("Channel")
    date = relationship("DateDim")

class ImageDetection(Base):
    __tablename__ = "fct_image_detections"
    __table_args__ = {'schema': 'marts'}
    
    detection_id = Column(Integer, primary_key=True)
    message_id = Column(Integer, index=True)
    channel_key = Column(Integer, ForeignKey('marts.dim_channels.channel_key'), index=True)
    date_key = Column(Integer, ForeignKey('marts.dim_dates.date_key'), index=True)
    image_path = Column(String(500))
    detection_count = Column(Integer)
    detected_classes = Column(Text)
    image_category = Column(String(50), index=True)
    confidence_score = Column(Float)
    has_person = Column(Boolean)
    has_product = Column(Boolean)
    content_strategy = Column(String(100))
    confidence_level = Column(String(50))
    processed_at = Column(DateTime)
    loaded_at = Column(DateTime, default=func.now())
    
    channel = relationship("Channel")
    date = relationship("DateDim")