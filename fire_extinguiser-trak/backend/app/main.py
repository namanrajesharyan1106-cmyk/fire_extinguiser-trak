"""
FastAPI Application Entry Point — Fire Safety Asset Management System v2

Startup:
- Creates all DB tables
- Auto-creates default ADMIN user if none exists
- Serves static files for uploads
- Registers all routers with RBAC
"""

import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .core.limiter import limiter
from .auth import create_default_admin
from .core.config import settings
from .core.database import Base, SessionLocal, engine
from .core.logger import logger
from .routers import (
    admin,
    assets,
    auth,
    dashboard,
    health,
    inspections,
    locations,
    maintenance,
    notifications,
    reports,
    search,
)

# ─── Create all DB tables ─────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ─── Ensure upload directories exist ─────────────────────────────────────────
os.makedirs(os.path.join(settings.UPLOAD_DIR, "qr"), exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "photos"), exist_ok=True)

# ─── FastAPI App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description="QR-Based Fire Safety Asset Management System for Manufacturing Plants",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

@app.on_event("startup")
def on_startup():
    db = SessionLocal()
    try:
        create_default_admin(db)
    finally:
        db.close()


# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import time
import uuid
from .core.logger import request_id_var

@app.middleware("http")
async def log_requests(request: Request, call_next):
    req_id = str(uuid.uuid4())
    request_id_var.set(req_id)
    
    request.state.request_id = req_id
    start_time = time.time()
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        logger.info(f"Completed {request.method} {request.url.path} with status {response.status_code} in {process_time:.4f}s")
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Failed {request.method} {request.url.path} in {process_time:.4f}s")
        raise e

# ─── Static Files (for serving uploaded images & QR codes) ───────────────────
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# ─── Startup Event ────────────────────────────────────────────────────────────
@app.on_event("startup")
def startup_event():
    from sqlalchemy import text
    import sys
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        logger.info("[STARTUP] Database connection established successfully.")
        create_default_admin(db)
    except Exception as e:
        logger.error(f"[STARTUP CRITICAL] Database connection failed or setup error: {e}")
        sys.exit(1)
    finally:
        db.close()


# ─── Exception Handlers ───────────────────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Validation Error",
            "data": None,
            "errors": exc.errors()
        },
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "data": None,
            "errors": {"status_code": exc.status_code, "path": str(request.url)},
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": str(exc),
            "data": None,
            "errors": {"status_code": 422},
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    import traceback
    
    req_id = getattr(request.state, "request_id", "-")
    logger.error(f"[ERROR] Unhandled exception (ReqID: {req_id}): {traceback.format_exc()}")
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "An internal server error occurred. Please contact support.",
            "data": None,
            "errors": {"status_code": 500, "request_id": req_id},
        },
    )


# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(locations.router, prefix="/api/locations", tags=["Locations"])
app.include_router(assets.router, prefix="/api/assets", tags=["Assets"])
app.include_router(inspections.router, prefix="/api/inspections", tags=["Inspections"])
app.include_router(maintenance.router, prefix="/api/maintenance", tags=["Maintenance"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(
    notifications.router, prefix="/api/notifications", tags=["Notifications"]
)
app.include_router(search.router, prefix="/api/search", tags=["Search"])
app.include_router(health.router, prefix="/health", tags=["Health"])



