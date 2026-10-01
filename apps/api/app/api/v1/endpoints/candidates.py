"""
CareerOS - Candidates endpoints (Phase 0 skeleton).
Full implementation in Phase 1.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/")
async def list_candidates(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """List candidates owned by the current user. (Phase 1 full implementation)"""
    return {"candidates": [], "total": 0, "phase": "1-pending"}


@router.get("/me")
async def get_my_candidate_profile(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Get the candidate profile for the authenticated user. (Phase 1)"""
    return {"user_id": str(current_user.id), "profile": None, "phase": "1-pending"}
