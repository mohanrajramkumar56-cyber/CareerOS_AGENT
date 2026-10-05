"""
CareerOS - Application Pydantic schemas (Phase 5).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ApplicationCreate(BaseModel):
    """Create a draft application."""
    job_id: uuid.UUID
    resume_id: Optional[uuid.UUID] = None
    cover_letter: Optional[str] = Field(default=None, max_length=5000)
    requires_approval: bool = True


class ApplicationApprove(BaseModel):
    """Approve an application for submission."""
    notes: Optional[str] = Field(default=None, max_length=1000)


class ApplicationResponse(BaseModel):
    """Full application representation."""
    id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: uuid.UUID
    resume_id: Optional[uuid.UUID]
    status: str
    cover_letter: Optional[str]
    form_data: Optional[str]
    requires_approval: bool
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    approval_notes: Optional[str]
    submitted_at: Optional[datetime]
    submission_method: Optional[str]
    submission_error: Optional[str]
    ats_application_id: Optional[str]
    confirmation_url: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApplicationListResponse(BaseModel):
    """Paginated application list."""
    applications: List[ApplicationResponse]
    total: int
    page: int
    page_size: int
