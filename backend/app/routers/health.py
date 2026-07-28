import time
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core import database
from ..core.config import settings

router = APIRouter()

START_TIME = time.time()

@router.get("")
def health_check():
    """Basic health check indicating if the application is running."""
    uptime = time.time() - START_TIME
    return {
        "status": "healthy",
        "uptime_seconds": round(uptime, 2),
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }

@router.get("/database")
def database_health_check(db: Session = Depends(database.get_db)):
    """Deep health check to verify database connectivity and latency."""
    try:
        start_time = time.time()
        db.execute(text("SELECT 1"))
        latency = time.time() - start_time
        return {
            "status": "healthy",
            "latency_ms": round(latency * 1000, 2)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@router.get("/application")
def application_health_check():
    """Detailed application health, can be extended with external service checks."""
    import psutil
    import os
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    return {
        "status": "healthy",
        "memory_rss_mb": round(memory_info.rss / (1024 * 1024), 2),
        "cpu_percent": process.cpu_percent(interval=0.1)
    }

@router.get("/version")
def version_info():
    """Returns application version and build environment details."""
    return {
        "title": settings.APP_TITLE,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }
