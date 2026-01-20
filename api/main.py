from fastapi import FastAPI, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
import pandas as pd
from sqlalchemy import text, func, desc, and_, or_

from . import crud, schemas, database
from .models import Message, Channel

app = FastAPI(
    title="Medical Telegram Analytics API",
    description="REST API for Ethiopian Medical Telegram Channel Analytics",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - API health check"""
    return {
        "message": "Medical Telegram Analytics API",
        "version": "2.0.0",
        "status": "operational",
        "endpoints": [
            "/docs - API Documentation",
            "/api/reports/top-products - Most mentioned products",
            "/api/channels/{name}/activity - Channel activity trends",
            "/api/search/messages - Search messages",
            "/api/reports/visual-content - Image analysis statistics"
        ]
    }

@app.get("/api/health", tags=["Health"])
async def health_check(db: Session = Depends(get_db)):
    """Health check with database connection test"""
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        
        # Get counts
        channel_count = db.query(Channel).count()
        message_count = db.query(Message).count()
        
        return {
            "status": "healthy",
            "database": "connected",
            "channels": channel_count,
            "messages": message_count,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}"
        )

@app.get("/api/reports/top-products", 
         response_model=List[schemas.TopProduct],
         tags=["Reports"])
async def get_top_products(
    limit: int = Query(10, ge=1, le=100, description="Number of top products to return"),
    days: int = Query(30, ge=1, description="Look back period in days"),
    channel_name: Optional[str] = Query(None, description="Filter by channel name"),
    min_occurrences: int = Query(2, ge=1, description="Minimum occurrences to include"),
    db: Session = Depends(get_db)
):
    """
    Get most frequently mentioned medical products across channels
    
    Extracts product names from message text using keyword matching and
    returns the most frequently mentioned products.
    """
    try:
        return await crud.get_top_products(
            db, 
            limit=limit, 
            days=days,
            channel_name=channel_name,
            min_occurrences=min_occurrences
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching top products: {str(e)}"
        )

@app.get("/api/channels/{channel_name}/activity",
         response_model=schemas.ChannelActivity,
         tags=["Channels"])
async def get_channel_activity(
    channel_name: str,
    period: str = Query("7d", regex="^(1d|7d|30d|90d)$", description="Time period: 1d,7d,30d,90d"),
    db: Session = Depends(get_db)
):
    """
    Get posting activity and engagement trends for a specific channel
    
    Returns daily metrics including message counts, views, forwards,
    and image usage for the specified period.
    """
    try:
        return await crud.get_channel_activity(db, channel_name, period)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching channel activity: {str(e)}"
        )

@app.get("/api/search/messages",
         response_model=schemas.MessageSearchResult,
         tags=["Search"])
async def search_messages(
    query: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    channel_name: Optional[str] = Query(None, description="Filter by channel"),
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    has_image: Optional[bool] = Query(None, description="Filter by image presence"),
    min_views: Optional[int] = Query(None, ge=0, description="Minimum views"),
    db: Session = Depends(get_db)
):
    """
    Search messages containing specific keywords
    
    Supports text search across message content with various filters.
    Returns paginated results with relevance scoring.
    """
    try:
        return await crud.search_messages(
            db,
            query=query,
            limit=limit,
            offset=offset,
            channel_name=channel_name,
            start_date=start_date,
            end_date=end_date,
            has_image=has_image,
            min_views=min_views
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search error: {str(e)}"
        )

@app.get("/api/reports/visual-content",
         response_model=schemas.VisualContentStats,
         tags=["Reports"])
async def get_visual_content_stats(
    group_by: str = Query("channel", regex="^(channel|category|date)$", 
                         description="Group by: channel, category, or date"),
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    min_confidence: float = Query(0.3, ge=0.0, le=1.0, description="Minimum detection confidence"),
    db: Session = Depends(get_db)
):
    """
    Get statistics about image usage and content analysis
    
    Analyzes visual content across channels including:
    - Image category distribution
    - Detection confidence metrics
    - Engagement comparison between image types
    """
    try:
        return await crud.get_visual_content_stats(
            db,
            group_by=group_by,
            start_date=start_date,
            end_date=end_date,
            min_confidence=min_confidence
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching visual content stats: {str(e)}"
        )

@app.get("/api/reports/engagement-trends",
         response_model=List[schemas.EngagementTrend],
         tags=["Reports"])
async def get_engagement_trends(
    metric: str = Query("views", regex="^(views|forwards|engagement)$",
                       description="Metric: views, forwards, or engagement"),
    window: str = Query("day", regex="^(hour|day|week|month)$",
                       description="Time window: hour, day, week, month"),
    db: Session = Depends(get_db)
):
    """
    Get engagement trends over time
    
    Returns time-series data for selected engagement metric
    aggregated by the specified time window.
    """
    try:
        return await crud.get_engagement_trends(db, metric=metric, window=window)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching engagement trends: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)