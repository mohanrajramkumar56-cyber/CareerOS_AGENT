"""
Browser session tracking for controlled application automation.
Each application gets one isolated browser session.
"""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, String, Text, func, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class BrowserSession(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "browser_sessions"

    # Ownership
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("applications.id", ondelete="SET NULL"), nullable=True, index=True)

    # State machine: pending | running | paused | completed | failed | expired
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)

    # Pause reason — populated when human takeover needed
    pause_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    # Type: captcha | unknown_field | legal_question | auth_challenge | payment
    pause_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Screenshot of the paused state (storage key)
    pause_screenshot_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Current URL at pause/failure
    current_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Structured form field data (JSON)
    form_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Human instruction after takeover
    human_instruction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Failure info
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_count: Mapped[int] = mapped_column(default=0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<BrowserSession id={self.id} status={self.status}>"
