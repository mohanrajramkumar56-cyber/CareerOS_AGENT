"""
CareerOS - Email + Follow-up ORM model (Phase 7).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class EmailMessage(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    An email message drafted or sent as part of the job search process.

    Types: application_followup | thank_you | networking | cold_outreach
    Status: draft | scheduled | sent | failed | cancelled
    """

    __tablename__ = "email_messages"

    # ── Ownership ─────────────────────────────────────────────────────────────
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Context ───────────────────────────────────────────────────────────────
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("applications.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Email fields ──────────────────────────────────────────────────────────
    email_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="application_followup", index=True
    )
    to_address: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    to_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Template ──────────────────────────────────────────────────────────────
    template_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # ── Scheduling ────────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="draft", index=True
    )
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    send_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Classification (Phase 7: Email Intelligence) ──────────────────────────
    classification: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )
    classification_confidence: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )

    # ── Follow-up tracking ────────────────────────────────────────────────────
    is_followup: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    followup_number: Mapped[int] = mapped_column(nullable=False, default=1)
    # Reference to prior email in the chain
    parent_email_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("email_messages.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<EmailMessage id={self.id} type={self.email_type} status={self.status}>"
