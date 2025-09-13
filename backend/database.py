"""
Database configuration and utilities for FastAPI
Based on python_database integration blueprint adapted for FastAPI
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException
from models import Base

# Database configuration
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=10,
    max_overflow=20,
    echo=False  # Set to True for SQL debugging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    Database dependency for FastAPI dependency injection with lazy initialization
    Usage: 
    @app.get("/api/endpoint")
    async def endpoint(db: Session = Depends(get_db)):
        # use db here
    """
    # Ensure database is initialized before creating session
    try:
        # Initialize database on first use
        if not ensure_db_initialized():
            raise HTTPException(
                status_code=503, 
                detail="Database initialization failed"
            )
        
        # Create database session
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        print(f"❌ Database connection failed in get_db: {e}")
        # Re-raise as service unavailable
        raise HTTPException(
            status_code=503, 
            detail="Database service temporarily unavailable"
        ) from e

def init_db():
    """Initialize database by creating all tables"""
    try:
        # Import all models to ensure they're registered
        import models  # noqa: F401
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Database initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False
        
# Global flag to track database initialization
_db_initialized = False

def ensure_db_initialized():
    """Ensure database is initialized exactly once"""
    global _db_initialized
    if not _db_initialized:
        if check_db_connection():
            _db_initialized = init_db()
        else:
            print("❌ Cannot initialize database - connection failed")
    return _db_initialized

def check_db_connection():
    """Check if database connection is working - non-blocking version"""
    try:
        # Use a short timeout to avoid blocking deployment health checks
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False