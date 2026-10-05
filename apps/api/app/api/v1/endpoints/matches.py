"""
CareerOS - Matching API endpoints (Phase 3).

Routes:
  POST /matches/compute         - compute match for current candidate vs a job
  GET  /matches/                - list all matches for current candidate
  GET  /matches/{job_id}        - get specific match for current candidate vs job
  POST /matches/batch           - compute matches for multiple jobs
"""
from __future__ import annotations

import uuid
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.match import MatchListResponse, MatchRequest, MatchResponse
from app.services import matching as svc
from app.services.candidate import get_profile_by_user
from app.services.job_service import get_job

router = APIRouter()


async def _get_candidate_or_404(db: AsyncSession, user: User):
    """Resolve user → candidate profile, raising 404 if not set up."""
    profile = await get_profile_by_user(db, user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found — set up your profile first",
        )
    return profile


# ── POST /matches/compute ─────────────────────────────────────────────────────

@router.post("/compute", response_model=MatchResponse, status_code=status.HTTP_200_OK)
async def compute_match(
    payload: MatchRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MatchResponse:
    """
    Compute (or recompute) the match between the current candidate and a job.

    Returns the persisted JobMatch with full scoring details.
    """
    candidate = await _get_candidate_or_404(db, current_user)
    job = await get_job(db, payload.job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    match = await svc.compute_match(db, job, candidate)
    return MatchResponse.model_validate(match)


# ── POST /matches/batch ───────────────────────────────────────────────────────

@router.post("/batch", status_code=status.HTTP_200_OK)
async def batch_compute_matches(
    payload: List[MatchRequest],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Compute matches for a list of job IDs.

    Returns count of matches computed and any failures.
    """
    if len(payload) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch limit is 50 jobs per request",
        )
    candidate = await _get_candidate_or_404(db, current_user)

    computed = 0
    failed: List[str] = []
    for req in payload:
        job = await get_job(db, req.job_id)
        if not job:
            failed.append(str(req.job_id))
            continue
        try:
            await svc.compute_match(db, job, candidate)
            computed += 1
        except Exception as e:
            failed.append(str(req.job_id))

    return {"computed": computed, "failed": failed}


# ── GET /matches/ ─────────────────────────────────────────────────────────────

@router.get("/", response_model=MatchListResponse)
async def list_matches(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    eligible_only: bool = Query(default=False, description="Only return eligible matches"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> MatchListResponse:
    """List all matches for the current candidate, sorted by confidence descending."""
    candidate = await _get_candidate_or_404(db, current_user)
    matches, total = await svc.get_matches_for_candidate(
        db, candidate.id, eligible_only=eligible_only, page=page, page_size=page_size
    )
    return MatchListResponse(
        matches=[MatchResponse.model_validate(m) for m in matches],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── GET /matches/{job_id} ─────────────────────────────────────────────────────

@router.get("/{job_id}", response_model=MatchResponse)
async def get_match(
    job_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MatchResponse:
    """Get the match result for the current candidate against a specific job."""
    candidate = await _get_candidate_or_404(db, current_user)
    from sqlalchemy.orm import joinedload
    from sqlalchemy import and_, select
    from app.models.job import JobMatch
    result = await db.execute(
        select(JobMatch)
        .options(joinedload(JobMatch.job))
        .where(
            and_(
                JobMatch.job_id == job_id,
                JobMatch.candidate_id == candidate.id,
            )
        )
    )
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    return MatchResponse.model_validate(match)
