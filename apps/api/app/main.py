"""
CareerOS API - Main FastAPI application entry point.
"""
from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import limiter
from app.db.session import close_engine, get_engine
from app.api.v1.router import api_router

settings = get_settings()

configure_logging(
    log_level=settings.log_level,
    json_logs=settings.is_production,
)

log = get_logger(__name__)

# ── Prometheus metrics ───────────────────────────────────────────────────────
REQUEST_COUNT = Counter(
    "careeros_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "careeros_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup → yield → shutdown."""
    log.info("careeros_api.startup", environment=settings.environment)
    # Validate DB connectivity on startup
    engine = get_engine()
    async with engine.connect():
        pass
    log.info("careeros_api.db_connected")
    yield
    log.info("careeros_api.shutdown")
    await close_engine()


app = FastAPI(
    title="CareerOS API",
    description="Autonomous AI Career Operating System — Backend API",
    version="0.1.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate limiting ─────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ── Security headers (Phase 10) ──────────────────────────────────────────────
from app.core.middleware import SecurityHeadersMiddleware, RequestSizeLimitMiddleware
app.add_middleware(SecurityHeadersMiddleware, is_production=settings.is_production)
app.add_middleware(RequestSizeLimitMiddleware)


# ── Correlation ID + metrics middleware ──────────────────────────────────────
@app.middleware("http")
async def observability_middleware(request: Request, call_next) -> Response:
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    correlation_id = request.headers.get("X-Correlation-ID", request_id)

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        correlation_id=correlation_id,
        method=request.method,
        path=request.url.path,
    )

    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        log.exception("careeros_api.unhandled_error", exc=str(exc))
        response = JSONResponse(status_code=500, content={"detail": "Internal server error"})

    duration = time.perf_counter() - start
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Correlation-ID"] = correlation_id

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code,
    ).inc()
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path,
    ).observe(duration)

    log.info(
        "careeros_api.request",
        status=response.status_code,
        duration_ms=round(duration * 1000, 2),
    )
    return response


# ── Routes ───────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "service": "careeros-api", "version": "0.1.0"}


@app.get("/ready", tags=["system"])
async def readiness() -> dict:
    """
    Readiness probe: checks DB connectivity.
    Returns 503 if database is not reachable.
    """
    from sqlalchemy import text
    from fastapi import HTTPException

    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as exc:
        log.error("careeros_api.readiness_failed", exc=str(exc))
        raise HTTPException(status_code=503, detail="Database not ready")


@app.get("/metrics", tags=["system"], include_in_schema=False)
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
