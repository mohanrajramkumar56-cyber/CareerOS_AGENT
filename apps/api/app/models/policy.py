"""
CareerOS - Policy + Audit ORM models (Phase 6).

PolicyRule: per-action autonomy configuration
AuditLog: immutable record of every significant action
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class PolicyRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Defines what the autonomous agent is allowed to do for a candidate.

    Examples:
    - action="application.submit" → requires_approval=True
    - action="email.send_followup" → requires_approval=False, max_per_day=3
    - action="resume.generate" → requires_approval=False
    """

    __tablename__ = "policy_rules"

    # ── Ownership ─────────────────────────────────────────────────────────────
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Action scope ──────────────────────────────────────────────────────────
    action: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True
    )
    # Examples: application.submit, email.send, resume.generate, job.discover

    # ── Policy settings ───────────────────────────────────────────────────────
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Rate limiting
    max_per_day: Mapped[Optional[int]] = mapped_column(nullable=True)
    max_per_week: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Conditions (JSON: {"min_match_score": 0.7, "eligible_only": true})
    conditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Notes / description
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<PolicyRule id={self.id} action={self.action} requires_approval={self.requires_approval}>"


class AuditLog(Base, UUIDPrimaryKeyMixin):
    """
    Immutable audit log entry.

    Every significant action (application, email, resume generation) is logged.
    Audit records are never soft-deleted — they are permanent.
    """

    __tablename__ = "audit_logs"

    # ── Actor ─────────────────────────────────────────────────────────────────
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    candidate_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Event ─────────────────────────────────────────────────────────────────
    action: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    resource_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # ── Context ───────────────────────────────────────────────────────────────
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # ── Result ────────────────────────────────────────────────────────────────
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Timestamp (immutable) ─────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action} success={self.success}>"
