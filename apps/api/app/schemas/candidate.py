"""
CareerOS - Candidate Pydantic schemas.

Separates request (input) from response (output) schemas.
Sensitive fields (salary) are never returned unless explicitly requested.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.domain.enums import (
    EmploymentType,
    EvidenceSourceType,
    EvidenceStrength,
    EvidenceStatus,
    FactCategory,
    RemoteType,
    WorkAuthorization,
)


# ── CandidateProfile ─────────────────────────────────────────────────────────

class CandidateProfileCreate(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=255)
    headline: Optional[str] = Field(default=None, max_length=500)
    summary: Optional[str] = None
    email: Optional[str] = Field(default=None, max_length=320)
    phone: Optional[str] = Field(default=None, max_length=50)
    linkedin_url: Optional[str] = Field(default=None, max_length=500)
    github_url: Optional[str] = Field(default=None, max_length=500)
    portfolio_url: Optional[str] = Field(default=None, max_length=500)
    website_url: Optional[str] = Field(default=None, max_length=500)
    current_city: Optional[str] = Field(default=None, max_length=255)
    current_state: Optional[str] = Field(default=None, max_length=255)
    current_country: Optional[str] = Field(default=None, max_length=100)
    willing_to_relocate: Optional[bool] = None
    preferred_remote_type: Optional[RemoteType] = None
    preferred_employment_type: Optional[EmploymentType] = None
    years_of_experience: Optional[int] = Field(default=None, ge=0, le=60)
    desired_title: Optional[str] = Field(default=None, max_length=255)
    salary_min_usd: Optional[int] = Field(default=None, ge=0)
    salary_max_usd: Optional[int] = Field(default=None, ge=0)
    work_authorization: Optional[WorkAuthorization] = None
    requires_visa_sponsorship: Optional[bool] = None


class CandidateProfileUpdate(CandidateProfileCreate):
    """Same fields as Create — all optional for partial update."""
    pass


class CandidateProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    full_name: Optional[str]
    headline: Optional[str]
    summary: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    linkedin_url: Optional[str]
    github_url: Optional[str]
    portfolio_url: Optional[str]
    website_url: Optional[str]
    current_city: Optional[str]
    current_state: Optional[str]
    current_country: Optional[str]
    willing_to_relocate: Optional[bool]
    preferred_remote_type: Optional[str]
    preferred_employment_type: Optional[str]
    years_of_experience: Optional[int]
    desired_title: Optional[str]
    work_authorization: Optional[str]
    requires_visa_sponsorship: Optional[bool]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Education ─────────────────────────────────────────────────────────────────

class EducationCreate(BaseModel):
    institution: str = Field(min_length=1, max_length=500)
    degree: Optional[str] = Field(default=None, max_length=255)
    field_of_study: Optional[str] = Field(default=None, max_length=255)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = False
    gpa: Optional[str] = Field(default=None, max_length=20)
    description: Optional[str] = None
    location: Optional[str] = Field(default=None, max_length=255)


class EducationUpdate(EducationCreate):
    institution: Optional[str] = Field(default=None, min_length=1, max_length=500)  # type: ignore[assignment]


class EducationResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    institution: str
    degree: Optional[str]
    field_of_study: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    is_current: bool
    gpa: Optional[str]
    description: Optional[str]
    location: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Experience ────────────────────────────────────────────────────────────────

class ExperienceCreate(BaseModel):
    company: str = Field(min_length=1, max_length=500)
    title: str = Field(min_length=1, max_length=500)
    location: Optional[str] = Field(default=None, max_length=255)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = False
    description: Optional[str] = None
    employment_type: Optional[EmploymentType] = None


class ExperienceUpdate(ExperienceCreate):
    company: Optional[str] = Field(default=None, min_length=1, max_length=500)  # type: ignore[assignment]
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)  # type: ignore[assignment]


class ExperienceResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    company: str
    title: str
    location: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    is_current: bool
    description: Optional[str]
    employment_type: Optional[str]
    duration_months: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Skill ─────────────────────────────────────────────────────────────────────

class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: Optional[str] = Field(default=None, max_length=100)
    proficiency_level: Optional[str] = Field(default=None, max_length=50)
    years_of_experience: Optional[int] = Field(default=None, ge=0, le=50)
    is_primary: bool = False


class SkillUpdate(BaseModel):
    category: Optional[str] = Field(default=None, max_length=100)
    proficiency_level: Optional[str] = Field(default=None, max_length=50)
    years_of_experience: Optional[int] = Field(default=None, ge=0, le=50)
    is_primary: Optional[bool] = None


class SkillResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    name: str
    category: Optional[str]
    proficiency_level: Optional[str]
    years_of_experience: Optional[int]
    is_primary: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Project ───────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    description: Optional[str] = None
    url: Optional[str] = Field(default=None, max_length=1000)
    repository_url: Optional[str] = Field(default=None, max_length=1000)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = False
    technologies: Optional[str] = None


class ProjectUpdate(ProjectCreate):
    name: Optional[str] = Field(default=None, min_length=1, max_length=500)  # type: ignore[assignment]


class ProjectResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    name: str
    description: Optional[str]
    url: Optional[str]
    repository_url: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    is_current: bool
    technologies: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Certification ─────────────────────────────────────────────────────────────

class CertificationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    issuing_organization: Optional[str] = Field(default=None, max_length=500)
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    credential_id: Optional[str] = Field(default=None, max_length=500)
    credential_url: Optional[str] = Field(default=None, max_length=1000)
    is_expired: bool = False


class CertificationUpdate(CertificationCreate):
    name: Optional[str] = Field(default=None, min_length=1, max_length=500)  # type: ignore[assignment]


class CertificationResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    name: str
    issuing_organization: Optional[str]
    issue_date: Optional[date]
    expiry_date: Optional[date]
    credential_id: Optional[str]
    credential_url: Optional[str]
    is_expired: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Achievement ───────────────────────────────────────────────────────────────

class AchievementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: Optional[str] = None
    issuing_organization: Optional[str] = Field(default=None, max_length=500)
    date_achieved: Optional[date] = None
    url: Optional[str] = Field(default=None, max_length=1000)


class AchievementUpdate(AchievementCreate):
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)  # type: ignore[assignment]


class AchievementResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    title: str
    description: Optional[str]
    issuing_organization: Optional[str]
    date_achieved: Optional[date]
    url: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Evidence Graph ────────────────────────────────────────────────────────────

class EvidenceCreate(BaseModel):
    source_type: EvidenceSourceType
    source_reference: Optional[str] = None
    description: Optional[str] = None


class EvidenceResponse(BaseModel):
    id: uuid.UUID
    fact_id: uuid.UUID
    source_type: str
    source_reference: Optional[str]
    description: Optional[str]
    strength: str
    status: str
    verified_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class CandidateFactCreate(BaseModel):
    category: FactCategory
    claim: str = Field(min_length=1, max_length=2000)
    normalized_value: Optional[str] = None
    evidence: Optional[List[EvidenceCreate]] = Field(default_factory=list)


class CandidateFactResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    category: str
    claim: str
    normalized_value: Optional[str]
    evidence_strength: str
    verified: bool
    confidence: Optional[float]
    represented_in_resume: bool
    evidence_entries: List[EvidenceResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Full profile (nested) ─────────────────────────────────────────────────────

class CandidateProfileFull(CandidateProfileResponse):
    """Complete candidate profile with all nested data."""
    education: List[EducationResponse] = []
    experiences: List[ExperienceResponse] = []
    skills: List[SkillResponse] = []
    projects: List[ProjectResponse] = []
    certifications: List[CertificationResponse] = []
    achievements: List[AchievementResponse] = []
    facts: List[CandidateFactResponse] = []
