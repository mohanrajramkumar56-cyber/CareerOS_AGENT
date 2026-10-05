"""
CareerOS - Application Engine Service (Phase 5).

Manages the full application lifecycle with state machine enforcement.

Key principles:
- State transitions are validated (cannot skip states)
- Submission (irreversible) requires human approval gate
- Form data is filled from verified candidate evidence only
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application, ApplicationStatus
from app.models.candidate_profile import CandidateProfile
from app.models.candidate import Skill, Experience
from app.models.job import Job


# ── State machine ─────────────────────────────────────────────────────────────

class InvalidTransitionError(Exception):
    """Raised when an invalid state machine transition is attempted."""


async def transition_status(
    db: AsyncSession,
    application: Application,
    to_status: str,
    actor: str = "user",
    notes: Optional[str] = None,
) -> Application:
    """
    Transition an application to a new status.

    Raises InvalidTransitionError if the transition is not allowed.
    """
    if not ApplicationStatus.can_transition(application.status, to_status):
        raise InvalidTransitionError(
            f"Cannot transition from '{application.status}' to '{to_status}'. "
            f"Allowed: {ApplicationStatus.TRANSITIONS.get(application.status, set())}"
        )

    application.status = to_status

    if to_status == ApplicationStatus.APPROVED:
        application.approved_by = actor
        application.approved_at = datetime.now(timezone.utc)
        if notes:
            application.approval_notes = notes

    elif to_status == ApplicationStatus.SUBMITTED:
        application.submitted_at = datetime.now(timezone.utc)

    elif to_status == ApplicationStatus.FAILED:
        if notes:
            application.submission_error = notes

    await db.flush()
    await db.refresh(application)
    return application


# ── Form filler ───────────────────────────────────────────────────────────────

def fill_form_from_candidate(
    candidate: CandidateProfile,
    skills: List[Any],
    experiences: List[Any],
    job: Job,
) -> Dict[str, Any]:
    """
    Generate form field values from verified candidate evidence.

    Returns a dict of common ATS field names → values.
    Only uses data from the candidate's verified profile.
    """
    form_data: Dict[str, Any] = {}

    # Personal info
    if candidate.full_name:
        parts = candidate.full_name.split(" ", 1)
        form_data["first_name"] = parts[0]
        form_data["last_name"] = parts[1] if len(parts) > 1 else ""
        form_data["full_name"] = candidate.full_name

    if candidate.email:
        form_data["email"] = candidate.email
    if candidate.phone:
        form_data["phone"] = candidate.phone

    # Location
    location_parts = filter(None, [candidate.current_city, candidate.current_state, candidate.current_country])
    form_data["location"] = ", ".join(location_parts)

    # Work authorization (only if disclosed)
    if candidate.work_authorization:
        form_data["work_authorization"] = candidate.work_authorization
    if candidate.requires_visa_sponsorship is not None:
        form_data["requires_sponsorship"] = str(candidate.requires_visa_sponsorship).lower()

    # Experience years
    if candidate.years_of_experience is not None:
        form_data["years_of_experience"] = candidate.years_of_experience

    # Skills summary
    if skills:
        form_data["skills_summary"] = ", ".join(s.name for s in skills[:15])

    # LinkedIn / portfolio
    if candidate.linkedin_url:
        form_data["linkedin_url"] = candidate.linkedin_url
    if candidate.github_url:
        form_data["github_url"] = candidate.github_url
    if candidate.portfolio_url:
        form_data["portfolio_url"] = candidate.portfolio_url
    if candidate.website_url:
        form_data["website_url"] = candidate.website_url

    # Remote / salary preferences
    if candidate.preferred_remote_type:
        form_data["remote_preference"] = candidate.preferred_remote_type

    # Job-specific
    form_data["job_title_applied"] = job.title
    form_data["company_applied"] = job.company

    return form_data


# ── CRUD ──────────────────────────────────────────────────────────────────────

async def create_application(
    db: AsyncSession,
    candidate: CandidateProfile,
    job: Job,
    resume_id: Optional[uuid.UUID] = None,
    cover_letter: Optional[str] = None,
    requires_approval: bool = True,
) -> Application:
    """
    Create a draft application for a job.

    Auto-fills form data from candidate evidence.
    """
    # Check for existing non-terminal application for this job
    existing = await db.execute(
        select(Application).where(
            and_(
                Application.candidate_id == candidate.id,
                Application.job_id == job.id,
                Application.status.not_in(list(ApplicationStatus.TERMINAL)),
                Application.deleted_at.is_(None),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError(f"An active application for this job already exists")

    # Load skills for form fill
    skills_r = await db.execute(
        select(Skill).where(and_(Skill.candidate_id == candidate.id, Skill.deleted_at.is_(None)))
    )
    skills = list(skills_r.scalars().all())

    experiences_r = await db.execute(
        select(Experience).where(and_(Experience.candidate_id == candidate.id, Experience.deleted_at.is_(None)))
    )
    experiences = list(experiences_r.scalars().all())

    # Fill form data
    form_data = fill_form_from_candidate(candidate, skills, experiences, job)

    application = Application(
        candidate_id=candidate.id,
        job_id=job.id,
        resume_id=resume_id,
        status=ApplicationStatus.DRAFT,
        cover_letter=cover_letter,
        form_data=json.dumps(form_data),
        requires_approval=requires_approval,
    )
    db.add(application)
    await db.flush()
    await db.refresh(application)
    return application


async def get_application(
    db: AsyncSession,
    application_id: uuid.UUID,
) -> Optional[Application]:
    """Fetch a non-deleted application by ID."""
    result = await db.execute(
        select(Application).where(
            and_(Application.id == application_id, Application.deleted_at.is_(None))
        )
    )
    return result.scalar_one_or_none()


async def list_applications(
    db: AsyncSession,
    candidate_id: uuid.UUID,
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Application], int]:
    """List applications for a candidate with optional status filter."""
    conditions = [
        Application.candidate_id == candidate_id,
        Application.deleted_at.is_(None),
    ]
    if status_filter:
        conditions.append(Application.status == status_filter)

    count_result = await db.execute(
        select(func.count()).select_from(Application).where(and_(*conditions))
    )
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        select(Application)
        .where(and_(*conditions))
        .order_by(Application.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def approve_application(
    db: AsyncSession,
    application: Application,
    approved_by: str = "user",
    notes: Optional[str] = None,
) -> Application:
    """Approve an application for submission (human approval gate)."""
    if application.status != ApplicationStatus.PENDING_APPROVAL:
        raise InvalidTransitionError(
            f"Application must be in pending_approval status to approve (current: {application.status})"
        )
    return await transition_status(db, application, ApplicationStatus.APPROVED, actor=approved_by, notes=notes)


async def submit_application(
    db: AsyncSession,
    application: Application,
    method: str = "manual",
) -> Application:
    """
    Mark an application as submitted.

    Requires prior approval if requires_approval=True.
    """
    if application.requires_approval and application.status != ApplicationStatus.APPROVED:
        raise InvalidTransitionError(
            "Application requires human approval before submission"
        )
    app = await transition_status(db, application, ApplicationStatus.SUBMITTED)
    app.submission_method = method
    await db.flush()
    await db.refresh(app)
    return app


async def withdraw_application(
    db: AsyncSession,
    application: Application,
) -> Application:
    """Withdraw an application."""
    return await transition_status(db, application, ApplicationStatus.WITHDRAWN)


async def delete_application(db: AsyncSession, application_id: uuid.UUID) -> bool:
    """Soft-delete a draft application."""
    application = await get_application(db, application_id)
    if not application:
        return False
    if application.status not in (ApplicationStatus.DRAFT, ApplicationStatus.WITHDRAWN, ApplicationStatus.FAILED):
        raise InvalidTransitionError("Only draft, withdrawn, or failed applications can be deleted")
    application.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return True
