"""
CareerOS - Candidate sub-models.

All sub-models belong to a CandidateProfile (cascade delete).
Each stores structured data plus optional free-text description.
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
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.candidate_profile import CandidateProfile


class Education(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Formal education history."""

    __tablename__ = "candidate_education"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    institution: Mapped[str] = mapped_column(String(500), nullable=False)
    degree: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    field_of_study: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    gpa: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    candidate: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile", back_populates="education"
    )

    def __repr__(self) -> str:
        return f"<Education id={self.id} institution={self.institution}>"


class Experience(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Work experience / employment history."""

    __tablename__ = "candidate_experiences"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    company: Mapped[str] = mapped_column(String(500), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    employment_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Computed months of experience (can be filled by service layer)
    duration_months: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    candidate: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile", back_populates="experiences"
    )

    def __repr__(self) -> str:
        return f"<Experience id={self.id} company={self.company} title={self.title}>"


class Skill(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    A skill claimed by the candidate.
    Must be backed by at least one CandidateFact to be used in applications.
    """

    __tablename__ = "candidate_skills"
    __table_args__ = (
        UniqueConstraint("candidate_id", "name", name="uq_candidate_skill_name"),
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # e.g. "programming_language", "framework", "tool"
    proficiency_level: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # beginner / intermediate / advanced / expert
    years_of_experience: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    candidate: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile", back_populates="skills"
    )

    def __repr__(self) -> str:
        return f"<Skill id={self.id} name={self.name}>"


class Project(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """A project built by the candidate."""

    __tablename__ = "candidate_projects"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    repository_url: Mapped[Optional[str]] = mapped_column(
        String(1000), nullable=True
    )
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    technologies: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # comma-separated for now; JSON in Phase 3

    candidate: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile", back_populates="projects"
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name}>"


class Certification(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """A professional certification held by the candidate."""

    __tablename__ = "candidate_certifications"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(500), nullable=False)
    issuing_organization: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    issue_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    credential_id: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    credential_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    is_expired: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    candidate: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile", back_populates="certifications"
    )

    def __repr__(self) -> str:
        return f"<Certification id={self.id} name={self.name}>"


class Achievement(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """A notable achievement, award, or recognition."""

    __tablename__ = "candidate_achievements"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    issuing_organization: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    date_achieved: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    candidate: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile", back_populates="achievements"
    )

    def __repr__(self) -> str:
        return f"<Achievement id={self.id} title={self.title}>"
