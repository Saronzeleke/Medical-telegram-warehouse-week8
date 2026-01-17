from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from . import crud, schemas, database

app = FastAPI(
    title="Medical Telegram Warehouse API",
    description="API for accessing Ethiopian medical Telegram channel data",
    version="1.0.0"
)

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
async def root():
    return {
        "message": "Medical Telegram Warehouse API",
        "version": "1.0.0",
        "endpoints": [
            "/channels",
            "/messages",
            "/stats/daily",
            "/stats/channels"
        ]
    }

@app.get("/channels", response_model=List[schemas.Channel])
async def get_channels(
    skip: int = 0,
    limit: int = 100,
    channel_type: Optional[str] = Query(None, description="Filter by channel type"),
    db: Session = Depends(get_db)
):
    """Get all channels with optional filtering"""
    return crud.get_channels(db, skip=skip, limit=limit, channel_type=channel_type)

@app.get("/channels/{channel_name}", response_model=schemas.ChannelDetail)
async def get_channel_detail(
    channel_name: str,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific channel"""
    channel = crud.get_channel_detail(db, channel_name)
    if channel is None:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel

@app.get("/messages", response_model=List[schemas.Message])
async def get_messages(
    skip: int = 0,
    limit: int = 100,
    channel_name: Optional[str] = Query(None, description="Filter by channel name"),
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    has_image: Optional[bool] = Query(None, description="Filter by image presence"),
    db: Session = Depends(get_db)
):
    """Get messages with various filters"""
    return crud.get_messages(
        db,
        skip=skip,
        limit=limit,
        channel_name=channel_name,
        start_date=start_date,
        end_date=end_date,
        has_image=has_image
    )

@app.get("/stats/daily", response_model=List[schemas.DailyStats])
async def get_daily_stats(
    start_date: Optional[date] = Query(None, description="Start date for stats"),
    end_date: Optional[date] = Query(None, description="End date for stats"),
    db: Session = Depends(get_db)
):
    """Get daily statistics aggregated across all channels"""
    return crud.get_daily_stats(db, start_date=start_date, end_date=end_date)

@app.get("/stats/channels", response_model=List[schemas.ChannelStats])
async def get_channel_stats(
    days: int = Query(30, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """Get channel statistics for the specified period"""
    return crud.get_channel_stats(db, days=days)

@app.get("/search")
async def search_messages(
    query: str = Query(..., description="Search query"),
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Search messages by text content"""
    return crud.search_messages(db, query=query, limit=limit)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)