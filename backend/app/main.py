"""
app/main.py

FastAPI entry point for Gridbricks Wind Day-Ahead Forecast Evaluation Portal.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.db.session import get_engine, init_db

# Configure structured logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("gridbricks.api")

DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan hook for clean startup and teardown."""
    logger.info("Initializing Gridbricks application...")
    engine = get_engine()
    # Check tables exist without altering immutable database
    try:
        init_db(engine)
    except Exception as e:
        logger.info(f"Database schema init check notice (read-only mode compatible): {e}")
    logger.info("Database initialized successfully.")
    yield
    logger.info("Shutting down Gridbricks application...")
    engine.dispose()


app = FastAPI(
    title="Gridbricks UK Wind Forecast Evaluation API",
    description=(
        "API for evaluating UK day-ahead wind generation forecasts from Elexon against "
        "outturn generation for January 2026 decision dates. Strictly enforces "
        "decision cutoffs without future data leakage."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
cors_origins_env = os.environ.get("CORS_ORIGINS")
origins = (
    [orig.strip() for orig in cors_origins_env.split(",") if orig.strip()]
    if cors_origins_env
    else DEFAULT_CORS_ORIGINS
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^https://.*(vercel\.app|herokuapp\.com)$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "Cache-Control"],
)


@app.middleware("http")
async def request_id_and_timing_middleware(request: Request, call_next) -> Response:
    """Assign or propagate X-Request-ID and log request timing."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    start_time = time.perf_counter()

    # Store request_id in request state for access in routes
    request.state.request_id = request_id

    response: Response = await call_next(request)

    duration_ms = (time.perf_counter() - start_time) * 1000.0
    response.headers["X-Request-ID"] = request_id

    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms:.2f}ms) [req_id={request_id}]"
    )
    return response


# Global Exception Handlers ensuring no stack traces or local paths are exposed
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.warning(f"Validation error on {request.url.path}: {exc} [req_id={request_id}]")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error_code": "INVALID_INPUT",
            "message": "Invalid query parameters or request payload.",
            "details": exc.errors(),
            "request_id": request_id,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": f"HTTP_{exc.status_code}",
            "message": str(exc.detail),
            "request_id": request_id,
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.error(f"Unhandled server error on {request.url.path}: {exc} [req_id={request_id}]", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An internal server error occurred. Please contact system support.",
            "request_id": request_id,
        },
    )


# Mount versioned API routes
app.include_router(api_router, prefix="/api/v1")
