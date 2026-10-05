"""
CareerOS - Resume ORM model (Phase 4).

Stores generated resumes with full provenance:
- Which candidate and optional target job
- Which template was used
- Rendered content (Markdown + optional PDF path)
- Truth policy status (never fabricated)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Resume(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """A generated, evidence-backed resume for a candidate."""

    __tablename__ = "resumes"

    # ── Ownership ─────────────────────────────────────────────────────────────
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Optional job targeting ────────────────────────────────────────────────
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Metadata ──────────────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="My Resume")
    template: Mapped[str] = mapped_column(
        String(100), nullable=False, default="standard"
    )  # standard | minimal | technical | executive

    # ── Content ───────────────────────────────────────────────────────────────
    content_markdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Storage ───────────────────────────────────────────────────────────────
    pdf_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    pdf_generated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Tailoring ─────────────────────────────────────────────────────────────
    # JSON list of skills emphasised in this version
    emphasised_skills: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # JSON list of evidence IDs used
    evidence_ids_used: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Truth policy ──────────────────────────────────────────────────────────
    # Tracks whether any unknown-strength facts were excluded
    facts_excluded_count: Mapped[int] = mapped_column(
        nullable=False, default=0
    )
    truth_policy_enforced: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    # ── Status ────────────────────────────────────────────────────────────────
    is_tailored: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(nullable=False, default=1)

    def __repr__(self) -> str:
        return f"<Resume id={self.id} candidate_id={self.candidate_id} template={self.template}>"
