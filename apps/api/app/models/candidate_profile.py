"""
CareerOS - CandidateProfile ORM model.

The CandidateProfile is the root of all candidate data.
It is owned by a User and contains:
- Identity and contact information
- Location preferences
- Employment preferences
- Work authorization
- Career automation policy reference

Sensitive fields (salary, location details) are stored separately
and accessed only with proper authorization.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.domain.enums import EmploymentType, RemoteType, WorkAuthorization
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.candidate import (
        Education,
        Experience,
        Skill,
        Project,
        Certification,
        Achievement,
    )
    from app.models.evidence import CandidateFact


class CandidateProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    Full candidate profile owned by a platform user.
    One user typically has one candidate profile (self-hosted model).
    """

    __tablename__ = "candidate_profiles"

    # ── Ownership ────────────────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # one profile per user
        index=True,
    )

    # ── Identity ─────────────────────────────────────────────────────────────
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    headline: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Contact ───────────────────────────────────────────────────────────────
    email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    github_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    portfolio_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    website_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # ── Location ──────────────────────────────────────────────────────────────
    current_city: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    current_state: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    current_country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    willing_to_relocate: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # ── Work Preferences ──────────────────────────────────────────────────────
    preferred_remote_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # RemoteType enum value
    preferred_employment_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # EmploymentType enum value
    years_of_experience: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    desired_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # ── Salary (sensitive — private by default) ────────────────────────────
    salary_min_usd: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_max_usd: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True, default="USD"
    )

    # ── Work Authorization ────────────────────────────────────────────────────
    work_authorization: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # WorkAuthorization enum value
    requires_visa_sponsorship: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True
    )

    # ── Profile completeness ──────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    education: Mapped[List["Education"]] = relationship(
        "Education", back_populates="candidate", cascade="all, delete-orphan"
    )
    experiences: Mapped[List["Experience"]] = relationship(
        "Experience", back_populates="candidate", cascade="all, delete-orphan"
    )
    skills: Mapped[List["Skill"]] = relationship(
        "Skill", back_populates="candidate", cascade="all, delete-orphan"
    )
    projects: Mapped[List["Project"]] = relationship(
        "Project", back_populates="candidate", cascade="all, delete-orphan"
    )
    certifications: Mapped[List["Certification"]] = relationship(
        "Certification", back_populates="candidate", cascade="all, delete-orphan"
    )
    achievements: Mapped[List["Achievement"]] = relationship(
        "Achievement", back_populates="candidate", cascade="all, delete-orphan"
    )
    facts: Mapped[List["CandidateFact"]] = relationship(
        "CandidateFact", back_populates="candidate", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CandidateProfile id={self.id} user_id={self.user_id}>"
