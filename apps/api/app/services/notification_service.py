"""
CareerOS Notification Service

Supports: structured logging (always), Telegram bot (optional).
All external adapters are optional — the service falls back gracefully
when credentials are not configured. Never raises to the caller.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


# ── Events ────────────────────────────────────────────────────────────────────

class NotificationEvent(str, Enum):
    APPLICATION_SUBMITTED = "application_submitted"
    APPLICATION_FAILED = "application_failed"
    HUMAN_APPROVAL_REQUIRED = "human_approval_required"
    CAPTCHA_ENCOUNTERED = "captcha_encountered"
    INTERVIEW_DETECTED = "interview_detected"
    ASSESSMENT_DETECTED = "assessment_detected"
    REJECTION_DETECTED = "rejection_detected"
    OFFER_DETECTED = "offer_detected"
    FOLLOWUP_SENT = "followup_sent"
    SYSTEM_FAILURE = "system_failure"


# ── Data ──────────────────────────────────────────────────────────────────────

@dataclass
class Notification:
    event: NotificationEvent
    title: str
    message: str
    user_id: Optional[str] = None
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None


# ── Adapters ──────────────────────────────────────────────────────────────────

class TelegramAdapter:
    """
    Send notifications via the Telegram Bot API.

    Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables.
    Silently disabled when either is missing.
    """

    def __init__(self) -> None:
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.enabled = bool(self.token and self.chat_id)

    async def send(self, notification: Notification) -> bool:
        if not self.enabled:
            return False
        try:
            import httpx  # noqa: PLC0415

            text = f"*{notification.title}*\n{notification.message}"
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    url,
                    json={
                        "chat_id": self.chat_id,
                        "text": text,
                        "parse_mode": "Markdown",
                    },
                )
                return resp.status_code == 200
        except Exception as exc:
            logger.error("Telegram notification failed: %s", exc)
            return False


# ── Service ───────────────────────────────────────────────────────────────────

class NotificationService:
    """
    Orchestrates notification delivery across all enabled adapters.

    Current adapters:
    - Structured log (always active)
    - Telegram (active when TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID are set)
    """

    def __init__(self) -> None:
        self.telegram = TelegramAdapter()

    async def notify(self, notification: Notification) -> None:
        """
        Deliver a notification to all enabled adapters.
        Never raises — errors are logged and swallowed.
        """
        logger.info(
            "notification event=%s title=%s resource_id=%s",
            notification.event,
            notification.title,
            notification.resource_id,
        )
        if self.telegram.enabled:
            await self.telegram.send(notification)

    # ── Convenience helpers ───────────────────────────────────────────────────

    async def notify_human_approval_required(
        self,
        application_id: str,
        job_title: str = "",
    ) -> None:
        """Notify that an application is waiting for human approval."""
        await self.notify(
            Notification(
                event=NotificationEvent.HUMAN_APPROVAL_REQUIRED,
                title="Approval Required",
                message=(
                    f"Application {application_id[:8]} for '{job_title}' "
                    "requires your approval before submission."
                ),
                resource_id=application_id,
                resource_type="application",
            )
        )

    async def notify_email_classified(
        self,
        category: str,
        subject: str,
        application_id: Optional[str] = None,
    ) -> None:
        """Notify when an inbound email has been classified."""
        event_map: dict[str, NotificationEvent] = {
            "interview": NotificationEvent.INTERVIEW_DETECTED,
            "rejection": NotificationEvent.REJECTION_DETECTED,
            "offer": NotificationEvent.OFFER_DETECTED,
            "assessment": NotificationEvent.ASSESSMENT_DETECTED,
        }
        event = event_map.get(category, NotificationEvent.APPLICATION_SUBMITTED)
        await self.notify(
            Notification(
                event=event,
                title=f"{category.replace('_', ' ').title()} Detected",
                message=f"Email classified as {category}: {subject[:80]}",
                resource_id=application_id,
                resource_type="application" if application_id else None,
            )
        )

    async def notify_application_submitted(
        self,
        application_id: str,
        job_title: str = "",
        company: str = "",
    ) -> None:
        """Notify that an application was successfully submitted."""
        await self.notify(
            Notification(
                event=NotificationEvent.APPLICATION_SUBMITTED,
                title="Application Submitted",
                message=f"Applied to '{job_title}' at {company}.",
                resource_id=application_id,
                resource_type="application",
            )
        )

    async def notify_system_failure(
        self,
        error_summary: str,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
    ) -> None:
        """Notify on a system-level failure."""
        await self.notify(
            Notification(
                event=NotificationEvent.SYSTEM_FAILURE,
                title="System Failure",
                message=error_summary[:200],
                resource_id=resource_id,
                resource_type=resource_type,
            )
        )


# ── Singleton ─────────────────────────────────────────────────────────────────

_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Return the process-level NotificationService singleton."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
