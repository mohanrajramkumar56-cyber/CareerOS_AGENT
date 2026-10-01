"""
CareerOS - Evidence Graph ORM models.

The evidence graph is the truth layer of CareerOS.

Architecture:
    CandidateFact  – a structured claim about the candidate
        └── Evidence (1..N) – pieces of evidence supporting the fact
            └── Each evidence entry has a source, strength, and verification status

Truth policy enforcement:
- A CandidateFact with no Evidence defaults to EvidenceStrength.UNKNOWN
- UNKNOWN facts MUST NOT appear in resumes or auto-filled applications
- Every Evidence entry must have a source_type
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.domain.enums import (
    EvidenceSourceType,
    EvidenceStatus,
    EvidenceStrength,
    FactCategory,
)
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.candidate_profile import CandidateProfile


class CandidateFact(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    A structured, verified fact about a candidate.

    This is the atomic unit of the evidence graph. Every fact must
    be backed by at least one Evidence entry to be used in applications.

    Example facts:
    - "Knows Python" (SKILL)
    - "Led team of 8 engineers at Acme Corp" (EXPERIENCE)
    - "AWS Certified Solutions Architect" (CERTIFICATION)
    """

    __tablename__ = "candidate_facts"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Category classifies what kind of fact this is
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # FactCategory enum value

    # The raw claim as the candidate stated it
    claim: Mapped[str] = mapped_column(Text, nullable=False)

    # Normalized / canonical form for matching
    normalized_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Aggregate evidence strength (computed from linked Evidence entries)
    evidence_strength: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=EvidenceStrength.UNKNOWN.value,
        index=True,
    )

    # Whether this fact has been explicitly verified
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Confidence score 0.0 → 1.0 (updated by validation service)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Whether this fact appears in the current resume
    represented_in_resume: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Relationships
    candidate: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile", back_populates="facts"
    )
    evidence_entries: Mapped[List["Evidence"]] = relationship(
        "Evidence", back_populates="fact", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<CandidateFact id={self.id} category={self.category} "
            f"strength={self.evidence_strength}>"
        )


class Evidence(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    A single piece of evidence supporting a CandidateFact.

    Multiple evidence entries can support the same fact,
    increasing the overall confidence.
    """

    __tablename__ = "candidate_evidence"

    fact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_facts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Source of this evidence
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # EvidenceSourceType enum value

    # Reference to the actual evidence (URL, document name, repo, etc.)
    source_reference: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Human-readable description of this evidence
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Evidence strength for this specific entry
    strength: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=EvidenceStrength.UNKNOWN.value,
    )

    # Verification status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=EvidenceStatus.UNVERIFIED.value,
    )

    # When this evidence was last verified
    verified_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationship
    fact: Mapped["CandidateFact"] = relationship(
        "CandidateFact", back_populates="evidence_entries"
    )

    def __repr__(self) -> str:
        return (
            f"<Evidence id={self.id} source_type={self.source_type} "
            f"strength={self.strength}>"
        )
