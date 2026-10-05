"""
CareerOS - Resume API endpoints (Phase 4).

Routes:
  POST   /resumes/          - generate a new resume
  GET    /resumes/          - list resumes for current candidate
  GET    /resumes/{id}      - get full resume content
  DELETE /resumes/{id}      - soft-delete a resume
  GET    /resumes/{id}/markdown - get raw markdown content
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.resume import ResumeCreate, ResumeListResponse, ResumeResponse, ResumeSummary
from app.services import resume_builder as svc
from app.services.candidate import get_profile_by_user
from app.services.job_service import get_job
from app.services.resume_export import markdown_to_docx, markdown_to_pdf

router = APIRouter()


async def _get_candidate_or_404(db, user):
    profile = await get_profile_by_user(db, user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found — set up your profile first",
        )
    return profile


# ── POST /resumes/ ────────────────────────────────────────────────────────────

@router.post("/", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
async def generate_resume(
    payload: ResumeCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResumeResponse:
    """
    Generate an evidence-backed resume.

    Optionally provide a job_id to create a tailored version.
    Truth policy strictly enforced — UNKNOWN facts excluded automatically.
    """
    candidate = await _get_candidate_or_404(db, current_user)

    job = None
    if payload.job_id:
        job = await get_job(db, payload.job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    try:
        resume = await svc.build_resume(
            db=db,
            candidate=candidate,
            template=payload.template,
            job=job,
            title=payload.title,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return ResumeResponse.model_validate(resume)


# ── GET /resumes/ ─────────────────────────────────────────────────────────────

@router.get("/", response_model=ResumeListResponse)
async def list_resumes(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ResumeListResponse:
    """List all resumes for the current candidate."""
    candidate = await _get_candidate_or_404(db, current_user)
    resumes, total = await svc.list_resumes(db, candidate.id, page=page, page_size=page_size)
    return ResumeListResponse(
        resumes=[ResumeSummary.model_validate(r) for r in resumes],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── GET /resumes/{id} ─────────────────────────────────────────────────────────

@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResumeResponse:
    """Get full resume content by ID."""
    candidate = await _get_candidate_or_404(db, current_user)
    resume = await svc.get_resume(db, resume_id)
    if not resume or resume.candidate_id != candidate.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    return ResumeResponse.model_validate(resume)


# ── GET /resumes/{id}/markdown ────────────────────────────────────────────────

@router.get("/{resume_id}/markdown", response_class=PlainTextResponse)
async def get_resume_markdown(
    resume_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> str:
    """Return the raw Markdown content of a resume."""
    candidate = await _get_candidate_or_404(db, current_user)
    resume = await svc.get_resume(db, resume_id)
    if not resume or resume.candidate_id != candidate.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    return resume.content_markdown or ""


# ── DELETE /resumes/{id} ──────────────────────────────────────────────────────

@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Soft-delete a resume."""
    candidate = await _get_candidate_or_404(db, current_user)
    resume = await svc.get_resume(db, resume_id)
    if not resume or resume.candidate_id != candidate.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    await svc.delete_resume(db, resume_id)



# ── GET /resumes/{id}/export/pdf ──────────────────────────────────────────────

@router.get("/{resume_id}/export/pdf")
async def export_resume_pdf(
    resume_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """
    Export resume as PDF.

    Returns a binary PDF file as an attachment.
    Requires markdown and weasyprint to be installed (503 if not available).
    """
    candidate = await _get_candidate_or_404(db, current_user)
    resume = await svc.get_resume(db, resume_id)
    if not resume or resume.candidate_id != candidate.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    try:
        pdf_bytes = markdown_to_pdf(resume.content_markdown or "", title=resume.title)
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Export dependencies not installed",
        ) from exc

    # Sanitise filename: strip characters that are unsafe in Content-Disposition
    safe_title = resume.title.replace('"', "'")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_title}.pdf"'},
    )


# ── GET /resumes/{id}/export/docx ─────────────────────────────────────────────

@router.get("/{resume_id}/export/docx")
async def export_resume_docx(
    resume_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """
    Export resume as DOCX.

    Returns a binary Word document (.docx) as an attachment.
    Requires python-docx to be installed (503 if not available).
    """
    candidate = await _get_candidate_or_404(db, current_user)
    resume = await svc.get_resume(db, resume_id)
    if not resume or resume.candidate_id != candidate.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    try:
        docx_bytes = markdown_to_docx(resume.content_markdown or "", title=resume.title)
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Export dependencies not installed",
        ) from exc

    # Sanitise filename: strip characters that are unsafe in Content-Disposition
    safe_title = resume.title.replace('"', "'")
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{safe_title}.docx"'},
    )
