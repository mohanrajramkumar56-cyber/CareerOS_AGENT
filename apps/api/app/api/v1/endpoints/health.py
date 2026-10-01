"""
CareerOS - System health endpoints.
"""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.db.session import get_engine

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    return {"status": "ok", "service": "careeros-api"}


@router.get("/db-health")
async def db_health() -> dict:
    """Check database connectivity."""
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": "disconnected", "detail": str(e)}
