from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from .logger import logger


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


async def generic_exception_handler(request: Request, exc: Exception):
    import traceback

    logger.error(f"[ERROR] Unhandled exception: {traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "An internal server error occurred. Please contact support.",
            "data": None,
            "errors": {"status_code": 500},
        },
    )
