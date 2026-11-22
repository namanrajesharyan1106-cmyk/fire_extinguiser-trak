import os
import time
from fastapi import APIRouter, Depends
import psutil
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..core import database
from ..core import dependencies as auth
from ..core.config import settings
from .. import models

router = APIRouter()

START_TIME = time.time()


@router.get("")
def health_check():
    """Basic public health check indicating if the application is running."""
    return {"status": "healthy"}


@router.get("/diagnostics")
def health_diagnostics(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("manage_system_config")),
):
    """Detailed system diagnostics for administrators only."""
    uptime = time.time() - START_TIME
    
    # DB Latency
    db_status = "healthy"
    latency_ms = None
    db_error = None
    try:
        t0 = time.time()
        db.execute(text("SELECT 1"))
        latency_ms = round((time.time() - t0) * 1000, 2)
    except Exception as e:
        db_status = "unhealthy"
        db_error = str(e)
        
    # Process / Memory / CPU
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "uptime_seconds": round(uptime, 2),
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": {
            "status": db_status,
            "latency_ms": latency_ms,
            "error": db_error,
        },
        "system": {
            "memory_rss_mb": round(memory_info.rss / (1024 * 1024), 2),
            "cpu_percent": process.cpu_percent(interval=0.1),
        },
    }
