"""
CareerOS - Resume Pydantic schemas (Phase 4).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ResumeCreate(BaseModel):
    """Request to generate a new resume."""
    template: str = Field(default="standard", pattern="^(standard|minimal|technical|executive)$")
    job_id: Optional[uuid.UUID] = None
    title: Optional[str] = Field(default=None, max_length=500)


class ResumeResponse(BaseModel):
    """Full resume representation."""
    id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: Optional[uuid.UUID]
    title: str
    template: str
    content_markdown: Optional[str]
    content_text: Optional[str]
    pdf_path: Optional[str]
    pdf_generated_at: Optional[datetime]
    emphasised_skills: Optional[str]
    evidence_ids_used: Optional[str]
    facts_excluded_count: int
    truth_policy_enforced: bool
    is_tailored: bool
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResumeSummary(BaseModel):
    """Lightweight resume list item — no content blobs."""
    id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: Optional[uuid.UUID]
    title: str
    template: str
    is_tailored: bool
    truth_policy_enforced: bool
    facts_excluded_count: int
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResumeListResponse(BaseModel):
    """Paginated resume list."""
    resumes: List[ResumeSummary]
    total: int
    page: int
    page_size: int
