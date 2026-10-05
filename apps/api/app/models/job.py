"""
CareerOS - Job ORM model.

Stores discovered jobs from external sources with full provenance.
Used for matching against candidate evidence and application automation.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.sqltypes import Enum as SQLEnum

from app.db.session import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.evidence import CandidateFact


class JobSource(str):
    """Supported job sources."""

    CAREER_SITE = "career_site"
    ATS = "ats"
    PUBLIC_API = "public_api"
    SEARCH = "search"
    EMAIL = "email"
    SCRAPED = "scraped"


class Job(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    A job discovered from an external source.

    Contains all raw + normalized fields with provenance for audit and deduplication.
    """

    __tablename__ = "jobs"

    # ── Source identifiers (for deduplication) ────────────────────────────────
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # JobSource enum value

    source_job_id: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, index=True
    )  # External system's ID

    source_url: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, index=True
    )  # Canonical URL

    # ── Content fields ────────────────────────────────────────────────────────
    company: Mapped[str] = mapped_column(String(500), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)

    location: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    remote_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # RemoteType enum
    employment_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # EmploymentType enum

    # Salary (optional, may be in description)
    salary_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True, default="USD"
    )
    salary_period: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # hourly / monthly / annually

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    responsibilities: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requirements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Extracted structured fields (Populated by extraction service)
    mandatory_skills: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # comma-separated
    preferred_skills: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # comma-separated
    education_requirements: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    experience_requirements: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    certifications: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    work_authorization_required: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True
    )
    sponsorship_required: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True
    )

    # ── Timestamps (for freshness logic) ──────────────────────────────────────
    posted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Freshness state ───────────────────────────────────────────────────────
    freshness_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        index=True,
    )  # new, active, stale, expired, unknown

    # ── Deduplication hash ────────────────────────────────────────────────────
    # SHA256 hash of title + company + location for detecting duplicates
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # ── Normalization status ──────────────────────────────────────────────────
    normalized_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    normalized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Application settings ──────────────────────────────────────────────────
    application_url: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Direct apply link

    # ── Relationships ─────────────────────────────────────────────────────────
    matches: Mapped[List["JobMatch"]] = relationship(
        "JobMatch", back_populates="job", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Job id={self.id} company={self.company} title={self.title}>"


class JobMatch(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    A match between a job and a candidate.

    Stores eligibility, skill gaps, and semantic similarity scores.
    """

    __tablename__ = "job_matches"

    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Hard eligibility
    eligible: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # eligible / ineligible / unknown

    hard_constraints_passed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    hard_constraints_failed: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Comma-separated list of failed constraints

    # Matching scores
    skill_match_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )  # 0.0 → 1.0
    semantic_similarity: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )  # pgvector cosine similarity

    # Requirements analysis
    matched_requirements: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON array
    missing_requirements: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON array

    # Skill gaps
    skill_gaps: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    representation_gaps: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Confidence
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Explanation (AI-generated match rationale)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship
    job: Mapped["Job"] = relationship("Job", back_populates="matches")

    __table_args__ = (
        UniqueConstraint("job_id", "candidate_id", name="uq_job_candidate_match"),
    )

    def __repr__(self) -> str:
        return f"<JobMatch id={self.id} job_id={self.job_id} candidate_id={self.candidate_id}>"
