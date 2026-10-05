"""
CareerOS - Jobs API endpoints (Phase 2).

Routes:
  POST   /jobs/                  - ingest a job (dedup-aware)
  GET    /jobs/                  - list jobs with pagination + filters
  GET    /jobs/{job_id}          - get a single job
  PUT    /jobs/{job_id}          - update job fields
  DELETE /jobs/{job_id}          - soft-delete a job
  POST   /jobs/search            - body-based search
  POST   /jobs/refresh-freshness - sweep freshness for all active jobs
"""
from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.job import (
    JobCreate,
    JobListResponse,
    JobResponse,
    JobSearchParams,
    JobUpdate,
)
from app.services import job_service as svc

router = APIRouter()


# ── POST /jobs/ ───────────────────────────────────────────────────────────────

@router.post("/", status_code=status.HTTP_201_CREATED)
async def ingest_job(
    payload: JobCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Ingest a job through the normalization + deduplication pipeline.

    Returns 201 with was_created=True for new jobs.
    Returns 200 with was_created=False for duplicates (idempotent).
    """
    job, was_created = await svc.create_job(db, payload.model_dump())
    # Explicitly refresh to load server-side defaults (created_at, updated_at)
    await db.refresh(job)
    job_response = JobResponse.model_validate(job)
    return {
        **job_response.model_dump(),
        "was_created": was_created,
    }


# ── GET /jobs/ ────────────────────────────────────────────────────────────────

@router.get("/", response_model=JobListResponse)
async def list_jobs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    query: Optional[str] = Query(default=None, description="Filter by title (ilike)"),
    company: Optional[str] = Query(default=None, description="Filter by company (ilike)"),
    remote_type: Optional[str] = Query(default=None, description="Filter by remote type"),
    employment_type: Optional[str] = Query(default=None, description="Filter by employment type"),
    freshness_status: Optional[str] = Query(default=None, description="Filter by freshness status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> JobListResponse:
    """List jobs with optional filters and pagination."""
    jobs, total = await svc.list_jobs(
        db,
        page=page,
        page_size=page_size,
        query=query,
        company=company,
        remote_type=remote_type,
        employment_type=employment_type,
        freshness_status=freshness_status,
    )
    return JobListResponse(
        jobs=[JobResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── GET /jobs/{job_id} ────────────────────────────────────────────────────────

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobResponse:
    """Get a single job by ID."""
    job = await svc.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobResponse.model_validate(job)


# ── PUT /jobs/{job_id} ────────────────────────────────────────────────────────

@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: uuid.UUID,
    payload: JobUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobResponse:
    """Update fields of an existing job."""
    job = await svc.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    updated = await svc.update_job(db, job, payload.model_dump(exclude_unset=True))
    return JobResponse.model_validate(updated)


# ── DELETE /jobs/{job_id} ─────────────────────────────────────────────────────

@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Soft-delete a job by setting deleted_at."""
    deleted = await svc.delete_job(db, job_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── POST /jobs/search ─────────────────────────────────────────────────────────

@router.post("/search", response_model=JobListResponse)
async def search_jobs(
    payload: JobSearchParams,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobListResponse:
    """
    Body-based search with text query and structured filters.

    Text query matches title or company via ilike.
    """
    filters = {
        k: v
        for k, v in {
            "company": payload.company,
            "remote_type": payload.remote_type,
            "employment_type": payload.employment_type,
            "freshness_status": payload.freshness_status,
        }.items()
        if v is not None
    }
    jobs, total = await svc.search_jobs(
        db,
        query=payload.query,
        filters=filters,
        page=payload.page,
        page_size=payload.page_size,
    )
    return JobListResponse(
        jobs=[JobResponse.model_validate(j) for j in jobs],
        total=total,
        page=payload.page,
        page_size=payload.page_size,
    )


# ── POST /jobs/refresh-freshness ──────────────────────────────────────────────

@router.post("/refresh-freshness")
async def refresh_freshness(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Sweep all active/new jobs and update their freshness status.

    Returns the number of jobs whose status changed.
    """
    updated = await svc.update_freshness(db)
    return {"updated": updated}
