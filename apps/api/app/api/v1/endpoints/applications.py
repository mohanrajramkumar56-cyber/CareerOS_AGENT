"""
CareerOS - Application API endpoints (Phase 5).

Routes:
  POST   /applications/                    - create draft application
  GET    /applications/                    - list candidate's applications
  GET    /applications/{id}               - get single application
  POST   /applications/{id}/submit        - request approval (draft → pending_approval)
  POST   /applications/{id}/approve       - approve (pending → approved) — human gate
  POST   /applications/{id}/reject        - reject (pending → rejected)
  POST   /applications/{id}/mark-submitted - mark as submitted (approved → submitted)
  POST   /applications/{id}/withdraw      - withdraw
  DELETE /applications/{id}               - delete draft
"""
from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.application import ApplicationStatus
from app.schemas.application import (
    ApplicationApprove,
    ApplicationCreate,
    ApplicationListResponse,
    ApplicationResponse,
)
from app.services import application_engine as svc
from app.services.candidate import get_profile_by_user
from app.services.job_service import get_job

router = APIRouter()


async def _get_candidate_or_404(db, user):
    profile = await get_profile_by_user(db, user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found",
        )
    return profile


async def _get_application_for_candidate(db, application_id, candidate_id):
    """Fetch application and verify ownership."""
    application = await svc.get_application(db, application_id)
    if not application or application.candidate_id != candidate_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return application


# ── POST /applications/ ───────────────────────────────────────────────────────

@router.post("/", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    payload: ApplicationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationResponse:
    """Create a draft application for a job. Auto-fills form data from candidate evidence."""
    candidate = await _get_candidate_or_404(db, current_user)
    job = await get_job(db, payload.job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    try:
        application = await svc.create_application(
            db=db,
            candidate=candidate,
            job=job,
            resume_id=payload.resume_id,
            cover_letter=payload.cover_letter,
            requires_approval=payload.requires_approval,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return ApplicationResponse.model_validate(application)


# ── GET /applications/ ────────────────────────────────────────────────────────

@router.get("/", response_model=ApplicationListResponse)
async def list_applications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: Optional[str] = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ApplicationListResponse:
    """List all applications for the current candidate."""
    candidate = await _get_candidate_or_404(db, current_user)
    applications, total = await svc.list_applications(
        db, candidate.id, status_filter=status_filter, page=page, page_size=page_size
    )
    return ApplicationListResponse(
        applications=[ApplicationResponse.model_validate(a) for a in applications],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── GET /applications/{id} ────────────────────────────────────────────────────

@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(
    application_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationResponse:
    """Get a single application by ID."""
    candidate = await _get_candidate_or_404(db, current_user)
    application = await _get_application_for_candidate(db, application_id, candidate.id)
    return ApplicationResponse.model_validate(application)


# ── POST /applications/{id}/submit ────────────────────────────────────────────

@router.post("/{application_id}/submit", response_model=ApplicationResponse)
async def request_submission(
    application_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationResponse:
    """Move application from draft to pending_approval (triggers approval gate)."""
    candidate = await _get_candidate_or_404(db, current_user)
    application = await _get_application_for_candidate(db, application_id, candidate.id)
    try:
        updated = await svc.transition_status(db, application, ApplicationStatus.PENDING_APPROVAL)
    except svc.InvalidTransitionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return ApplicationResponse.model_validate(updated)


# ── POST /applications/{id}/approve ──────────────────────────────────────────

@router.post("/{application_id}/approve", response_model=ApplicationResponse)
async def approve_application(
    application_id: uuid.UUID,
    payload: ApplicationApprove,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationResponse:
    """Human approval gate — approve the application for submission."""
    candidate = await _get_candidate_or_404(db, current_user)
    application = await _get_application_for_candidate(db, application_id, candidate.id)
    try:
        updated = await svc.approve_application(
            db, application, approved_by=str(current_user.id), notes=payload.notes
        )
    except svc.InvalidTransitionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return ApplicationResponse.model_validate(updated)


# ── POST /applications/{id}/reject ───────────────────────────────────────────

@router.post("/{application_id}/reject", response_model=ApplicationResponse)
async def reject_application(
    application_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationResponse:
    """Reject an application (human rejects the draft)."""
    candidate = await _get_candidate_or_404(db, current_user)
    application = await _get_application_for_candidate(db, application_id, candidate.id)
    try:
        updated = await svc.transition_status(db, application, ApplicationStatus.REJECTED)
    except svc.InvalidTransitionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return ApplicationResponse.model_validate(updated)


# ── POST /applications/{id}/mark-submitted ────────────────────────────────────

@router.post("/{application_id}/mark-submitted", response_model=ApplicationResponse)
async def mark_submitted(
    application_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationResponse:
    """Mark an approved application as actually submitted."""
    candidate = await _get_candidate_or_404(db, current_user)
    application = await _get_application_for_candidate(db, application_id, candidate.id)
    try:
        updated = await svc.submit_application(db, application, method="manual")
    except svc.InvalidTransitionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return ApplicationResponse.model_validate(updated)


# ── POST /applications/{id}/withdraw ─────────────────────────────────────────

@router.post("/{application_id}/withdraw", response_model=ApplicationResponse)
async def withdraw_application(
    application_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationResponse:
    """Withdraw an application."""
    candidate = await _get_candidate_or_404(db, current_user)
    application = await _get_application_for_candidate(db, application_id, candidate.id)
    try:
        updated = await svc.withdraw_application(db, application)
    except svc.InvalidTransitionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return ApplicationResponse.model_validate(updated)


# ── DELETE /applications/{id} ─────────────────────────────────────────────────

@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(
    application_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a draft or withdrawn application."""
    candidate = await _get_candidate_or_404(db, current_user)
    application = await _get_application_for_candidate(db, application_id, candidate.id)
    try:
        await svc.delete_application(db, application_id)
    except svc.InvalidTransitionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
