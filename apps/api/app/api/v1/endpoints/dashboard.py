"""
CareerOS - Dashboard stats endpoint (Phase 8).

Aggregates key metrics for the current candidate's dashboard.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.application import Application, ApplicationStatus
from app.models.job import Job, JobMatch
from app.models.resume import Resume
from app.services.candidate import get_profile_by_user

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Return aggregated dashboard statistics for the current user.
    Returns zeros if no candidate profile exists yet.
    """
    profile = await get_profile_by_user(db, current_user.id)
    if not profile:
        return {
            "jobs_discovered": 0,
            "jobs_matched": 0,
            "jobs_eligible": 0,
            "resumes_generated": 0,
            "applications_total": 0,
            "applications_pending_approval": 0,
            "applications_submitted": 0,
            "applications_draft": 0,
        }

    candidate_id = profile.id

    # Total jobs in system
    jobs_r = await db.execute(
        select(func.count()).select_from(Job).where(Job.deleted_at.is_(None))
    )
    jobs_discovered = jobs_r.scalar_one()

    # Matches computed for this candidate
    matches_r = await db.execute(
        select(func.count()).select_from(JobMatch).where(
            JobMatch.candidate_id == candidate_id
        )
    )
    jobs_matched = matches_r.scalar_one()

    # Eligible matches
    eligible_r = await db.execute(
        select(func.count()).select_from(JobMatch).where(
            and_(
                JobMatch.candidate_id == candidate_id,
                JobMatch.eligible == "eligible",
            )
        )
    )
    jobs_eligible = eligible_r.scalar_one()

    # Resumes
    resumes_r = await db.execute(
        select(func.count()).select_from(Resume).where(
            and_(Resume.candidate_id == candidate_id, Resume.deleted_at.is_(None))
        )
    )
    resumes_generated = resumes_r.scalar_one()

    # Applications
    apps_r = await db.execute(
        select(func.count()).select_from(Application).where(
            and_(Application.candidate_id == candidate_id, Application.deleted_at.is_(None))
        )
    )
    applications_total = apps_r.scalar_one()

    pending_r = await db.execute(
        select(func.count()).select_from(Application).where(
            and_(
                Application.candidate_id == candidate_id,
                Application.status == ApplicationStatus.PENDING_APPROVAL,
                Application.deleted_at.is_(None),
            )
        )
    )
    applications_pending = pending_r.scalar_one()

    submitted_r = await db.execute(
        select(func.count()).select_from(Application).where(
            and_(
                Application.candidate_id == candidate_id,
                Application.status.in_([ApplicationStatus.SUBMITTED, ApplicationStatus.ACKNOWLEDGED]),
                Application.deleted_at.is_(None),
            )
        )
    )
    applications_submitted = submitted_r.scalar_one()

    draft_r = await db.execute(
        select(func.count()).select_from(Application).where(
            and_(
                Application.candidate_id == candidate_id,
                Application.status == ApplicationStatus.DRAFT,
                Application.deleted_at.is_(None),
            )
        )
    )
    applications_draft = draft_r.scalar_one()

    return {
        "jobs_discovered": jobs_discovered,
        "jobs_matched": jobs_matched,
        "jobs_eligible": jobs_eligible,
        "resumes_generated": resumes_generated,
        "applications_total": applications_total,
        "applications_pending_approval": applications_pending,
        "applications_submitted": applications_submitted,
        "applications_draft": applications_draft,
    }


@router.get("/activity")
async def get_recent_activity(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Return recent activity items for the dashboard feed."""
    profile = await get_profile_by_user(db, current_user.id)
    if not profile:
        return {"items": []}

    candidate_id = profile.id
    items = []

    # Recent applications
    apps_result = await db.execute(
        select(Application)
        .where(and_(Application.candidate_id == candidate_id, Application.deleted_at.is_(None)))
        .order_by(Application.updated_at.desc())
        .limit(5)
    )
    for app in apps_result.scalars().all():
        items.append({
            "type": "application",
            "status": app.status,
            "timestamp": app.updated_at.isoformat() if app.updated_at else None,
            "resource_id": str(app.id),
        })

    # Recent resumes
    resumes_result = await db.execute(
        select(Resume)
        .where(and_(Resume.candidate_id == candidate_id, Resume.deleted_at.is_(None)))
        .order_by(Resume.created_at.desc())
        .limit(3)
    )
    for resume in resumes_result.scalars().all():
        items.append({
            "type": "resume",
            "title": resume.title,
            "template": resume.template,
            "timestamp": resume.created_at.isoformat() if resume.created_at else None,
            "resource_id": str(resume.id),
        })

    # Sort by timestamp
    items.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    return {"items": items[:10]}
