"""
CareerOS - Application ORM model (Phase 5).

State machine: draft → pending_approval → approved → submitted → acknowledged
                     ↘ rejected (human rejects)
                     ↘ failed (submission error)
                     ↘ withdrawn (candidate cancels)

Irreversible actions (submit) require human approval gate.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ApplicationStatus:
    """Application state machine states."""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    REJECTED = "rejected"           # Human rejected the draft
    FAILED = "failed"               # Submission error
    WITHDRAWN = "withdrawn"         # Candidate cancelled

    TERMINAL = {SUBMITTED, ACKNOWLEDGED, REJECTED, FAILED, WITHDRAWN}
    TRANSITIONS = {
        DRAFT: {PENDING_APPROVAL, WITHDRAWN},
        PENDING_APPROVAL: {APPROVED, REJECTED},
        APPROVED: {SUBMITTED, WITHDRAWN},
        SUBMITTED: {ACKNOWLEDGED, FAILED},
        ACKNOWLEDGED: set(),
        REJECTED: set(),
        FAILED: {DRAFT},            # Can retry from failed
        WITHDRAWN: set(),
    }

    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        return to_status in cls.TRANSITIONS.get(from_status, set())


class Application(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    An application to a job on behalf of a candidate.

    Immutable after submission (per truth policy).
    """

    __tablename__ = "applications"

    # ── Ownership ─────────────────────────────────────────────────────────────
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Target job ────────────────────────────────────────────────────────────
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Attached resume ───────────────────────────────────────────────────────
    resume_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("resumes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── State machine ─────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=ApplicationStatus.DRAFT, index=True
    )

    # ── Application content (form fill) ──────────────────────────────────────
    cover_letter: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    form_data: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON: {field_name: value}

    # ── Approval gate ─────────────────────────────────────────────────────────
    requires_approval: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    approved_by: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # "user" or system identifier
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approval_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Submission ────────────────────────────────────────────────────────────
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    submission_method: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # "browser_automation" | "api" | "manual"
    submission_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Outcome tracking ──────────────────────────────────────────────────────
    ats_application_id: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )  # ID from ATS system after submission
    confirmation_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Notes ─────────────────────────────────────────────────────────────────
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Application id={self.id} job_id={self.job_id} status={self.status}>"
