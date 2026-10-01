"""
CareerOS - Jobs endpoints (Phase 0 skeleton).
Full implementation in Phase 2.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/")
async def list_jobs(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """List discovered jobs. (Phase 2 full implementation)"""
    return {"jobs": [], "total": 0, "phase": "2-pending"}
