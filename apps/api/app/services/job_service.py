"""
CareerOS - Job service layer.

Wraps the job_pipeline for CRUD operations and search.
All functions are async and take an AsyncSession.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.services.job_pipeline import ingest_job, update_stale_jobs


# ── Create ────────────────────────────────────────────────────────────────────

async def create_job(
    db: AsyncSession,
    job_data: Dict[str, Any],
) -> Tuple[Job, bool]:
    """
    Ingest a job through the pipeline.

    Returns (job, was_created).
    Duplicate jobs return was_created=False with last_verified_at refreshed.
    """
    return await ingest_job(db, job_data)


# ── Read ──────────────────────────────────────────────────────────────────────

async def get_job(
    db: AsyncSession,
    job_id: uuid.UUID,
) -> Optional[Job]:
    """Fetch a single non-deleted job by ID."""
    result = await db.execute(
        select(Job).where(
            and_(
                Job.id == job_id,
                Job.deleted_at.is_(None),
            )
        )
    )
    return result.scalar_one_or_none()


async def list_jobs(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    **filters: Any,
) -> Tuple[List[Job], int]:
    """
    Return a paginated list of non-deleted jobs with optional filters.

    Supported filter kwargs:
    - query: str — ilike match on title
    - company: str — ilike match on company
    - remote_type: str — exact match
    - employment_type: str — exact match
    - freshness_status: str — exact match
    """
    conditions = [Job.deleted_at.is_(None)]

    query_text: Optional[str] = filters.get("query")
    if query_text:
        conditions.append(Job.title.ilike(f"%{query_text}%"))

    company: Optional[str] = filters.get("company")
    if company:
        conditions.append(Job.company.ilike(f"%{company}%"))

    remote_type: Optional[str] = filters.get("remote_type")
    if remote_type:
        conditions.append(Job.remote_type == remote_type)

    employment_type: Optional[str] = filters.get("employment_type")
    if employment_type:
        conditions.append(Job.employment_type == employment_type)

    freshness_status: Optional[str] = filters.get("freshness_status")
    if freshness_status:
        conditions.append(Job.freshness_status == freshness_status)

    # Total count
    count_result = await db.execute(
        select(func.count()).select_from(Job).where(and_(*conditions))
    )
    total = count_result.scalar_one()

    # Paginated results
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Job)
        .where(and_(*conditions))
        .order_by(Job.discovered_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    jobs = list(result.scalars().all())

    return jobs, total


async def search_jobs(
    db: AsyncSession,
    query: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Job], int]:
    """
    Search jobs by text query and structured filters.

    Text query matches title OR company (ilike).
    Additional filters are applied as AND conditions.
    """
    conditions = [Job.deleted_at.is_(None)]

    if query:
        conditions.append(
            or_(
                Job.title.ilike(f"%{query}%"),
                Job.company.ilike(f"%{query}%"),
            )
        )

    if filters:
        company: Optional[str] = filters.get("company")
        if company:
            conditions.append(Job.company.ilike(f"%{company}%"))

        remote_type: Optional[str] = filters.get("remote_type")
        if remote_type:
            conditions.append(Job.remote_type == remote_type)

        employment_type: Optional[str] = filters.get("employment_type")
        if employment_type:
            conditions.append(Job.employment_type == employment_type)

        freshness_status: Optional[str] = filters.get("freshness_status")
        if freshness_status:
            conditions.append(Job.freshness_status == freshness_status)

    # Total count
    count_result = await db.execute(
        select(func.count()).select_from(Job).where(and_(*conditions))
    )
    total = count_result.scalar_one()

    # Paginated results
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Job)
        .where(and_(*conditions))
        .order_by(Job.discovered_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    jobs = list(result.scalars().all())

    return jobs, total


# ── Update ────────────────────────────────────────────────────────────────────

async def update_job(
    db: AsyncSession,
    job: Job,
    update_data: Dict[str, Any],
) -> Job:
    """Apply a partial update to an existing job and flush."""
    for field, value in update_data.items():
        if hasattr(job, field):
            setattr(job, field, value)
    await db.flush()
    await db.refresh(job)
    return job


# ── Delete ────────────────────────────────────────────────────────────────────

async def delete_job(
    db: AsyncSession,
    job_id: uuid.UUID,
) -> bool:
    """
    Soft-delete a job by setting deleted_at.

    Returns True if found and deleted, False if not found.
    """
    job = await get_job(db, job_id)
    if not job:
        return False
    job.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return True


# ── Freshness ─────────────────────────────────────────────────────────────────

async def update_freshness(db: AsyncSession) -> int:
    """
    Trigger a freshness sweep across all active/new jobs.

    Returns the count of jobs whose freshness_status changed.
    """
    return await update_stale_jobs(db)
