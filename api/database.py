"""
Database connection configuration for FastAPI
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection URL
DATABASE_URL = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST', 'postgres')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB')}"

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    pool_size=20,  # Increased for API
    max_overflow=40,
    pool_pre_ping=True,  # Verify connections
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=False  # Set to True for SQL logging
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()

# Dependency to get DB session
def get_db():
    """
    FastAPI dependency that provides a database session.
    
    Usage:
    @app.get("/items")
    def read_items(db: Session = Depends(get_db)):
        return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Health check function
def check_database_connection():
    """Check if database is accessible"""
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"Database connection error: {e}")
        return False

# Initialize database tables (optional)
def init_db():
    """Initialize database tables"""
    try:
        # Import models here to avoid circular imports
        from . import models
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully")
    except Exception as e:
        print(f"Database initialization error: {e}")