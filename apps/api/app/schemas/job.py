"""
CareerOS - Job Pydantic schemas.

Separates request (input) from response (output) schemas.
Follows the same pattern as schemas/candidate.py.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ── JobCreate ─────────────────────────────────────────────────────────────────

class JobCreate(BaseModel):
    """Schema for ingesting a new job."""

    # Required fields
    source: str = Field(min_length=1, max_length=50)
    company: str = Field(min_length=1, max_length=500)
    title: str = Field(min_length=1, max_length=500)

    # Optional provenance
    source_job_id: Optional[str] = Field(default=None, max_length=500)
    source_url: Optional[str] = None

    # Optional content fields
    location: Optional[str] = Field(default=None, max_length=500)
    remote_type: Optional[str] = Field(default=None, max_length=50)
    employment_type: Optional[str] = Field(default=None, max_length=50)

    # Salary
    salary_min: Optional[int] = Field(default=None, ge=0)
    salary_max: Optional[int] = Field(default=None, ge=0)
    salary_currency: Optional[str] = Field(default=None, max_length=10)
    salary_period: Optional[str] = Field(default=None, max_length=20)

    # Description blobs
    description: Optional[str] = None
    responsibilities: Optional[str] = None
    requirements: Optional[str] = None

    # Skills (comma-separated strings)
    mandatory_skills: Optional[str] = None
    preferred_skills: Optional[str] = None

    # Requirements
    education_requirements: Optional[str] = None
    experience_requirements: Optional[str] = None
    certifications: Optional[str] = None
    work_authorization_required: Optional[bool] = None
    sponsorship_required: Optional[bool] = None

    # Application
    application_url: Optional[str] = None

    # Timing
    posted_at: Optional[datetime] = None


# ── JobUpdate ─────────────────────────────────────────────────────────────────

class JobUpdate(BaseModel):
    """Schema for updating an existing job — all fields optional."""

    source: Optional[str] = Field(default=None, max_length=50)
    source_job_id: Optional[str] = Field(default=None, max_length=500)
    source_url: Optional[str] = None
    company: Optional[str] = Field(default=None, max_length=500)
    title: Optional[str] = Field(default=None, max_length=500)
    location: Optional[str] = Field(default=None, max_length=500)
    remote_type: Optional[str] = Field(default=None, max_length=50)
    employment_type: Optional[str] = Field(default=None, max_length=50)
    salary_min: Optional[int] = Field(default=None, ge=0)
    salary_max: Optional[int] = Field(default=None, ge=0)
    salary_currency: Optional[str] = Field(default=None, max_length=10)
    salary_period: Optional[str] = Field(default=None, max_length=20)
    description: Optional[str] = None
    responsibilities: Optional[str] = None
    requirements: Optional[str] = None
    application_url: Optional[str] = None
    posted_at: Optional[datetime] = None
    freshness_status: Optional[str] = Field(default=None, max_length=20)


# ── JobResponse ───────────────────────────────────────────────────────────────

class JobResponse(BaseModel):
    """Full job representation returned to clients. Excludes deleted_at."""

    id: uuid.UUID
    source: str
    source_job_id: Optional[str]
    source_url: Optional[str]
    company: str
    title: str
    location: Optional[str]
    remote_type: Optional[str]
    employment_type: Optional[str]
    salary_min: Optional[int]
    salary_max: Optional[int]
    salary_currency: Optional[str]
    salary_period: Optional[str]
    description: Optional[str]
    responsibilities: Optional[str]
    requirements: Optional[str]
    mandatory_skills: Optional[str]
    preferred_skills: Optional[str]
    education_requirements: Optional[str]
    experience_requirements: Optional[str]
    certifications: Optional[str]
    work_authorization_required: Optional[bool]
    sponsorship_required: Optional[bool]
    posted_at: Optional[datetime]
    discovered_at: datetime
    last_verified_at: Optional[datetime]
    expires_at: Optional[datetime]
    freshness_status: str
    content_hash: str
    normalized: bool
    normalized_at: Optional[datetime]
    application_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── JobListResponse ───────────────────────────────────────────────────────────

class JobListResponse(BaseModel):
    """Paginated list of jobs."""

    jobs: List[JobResponse]
    total: int
    page: int
    page_size: int


# ── JobSearchParams ───────────────────────────────────────────────────────────

class JobSearchParams(BaseModel):
    """Body parameters for POST /jobs/search."""

    query: Optional[str] = None
    company: Optional[str] = None
    remote_type: Optional[str] = None
    employment_type: Optional[str] = None
    freshness_status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# ── JobMatchResponse ──────────────────────────────────────────────────────────

class JobMatchResponse(BaseModel):
    """A match between a job and a candidate, with the job embedded."""

    id: uuid.UUID
    job_id: uuid.UUID
    candidate_id: uuid.UUID
    eligible: str
    hard_constraints_passed: bool
    hard_constraints_failed: Optional[str]
    skill_match_score: Optional[float]
    semantic_similarity: Optional[float]
    matched_requirements: Optional[str]
    missing_requirements: Optional[str]
    skill_gaps: Optional[str]
    representation_gaps: Optional[str]
    confidence: Optional[float]
    explanation: Optional[str]
    created_at: datetime
    updated_at: datetime

    # Nested job
    job: JobResponse

    model_config = {"from_attributes": True}
