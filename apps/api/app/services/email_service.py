"""
CareerOS - Email + Follow-up Service (Phase 7).

Manages:
- Email template rendering (Jinja2-style simple templates)
- Follow-up scheduling logic
- Email CRUD
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_message import EmailMessage
from app.models.candidate_profile import CandidateProfile


# ── Email templates ───────────────────────────────────────────────────────────

EMAIL_TEMPLATES: Dict[str, Dict[str, str]] = {
    "application_followup": {
        "subject": "Following up on my application — {job_title} at {company}",
        "body": (
            "Hi {recipient_name},\n\n"
            "I wanted to follow up on my application for the {job_title} position at {company}. "
            "I remain very interested in this opportunity and would love to learn more about next steps.\n\n"
            "Please don't hesitate to reach out if you need any additional information.\n\n"
            "Best regards,\n{candidate_name}"
        ),
    },
    "thank_you": {
        "subject": "Thank you — {job_title} interview at {company}",
        "body": (
            "Hi {recipient_name},\n\n"
            "Thank you for taking the time to speak with me about the {job_title} role at {company}. "
            "I enjoyed learning more about the team and I'm excited about the possibility of contributing.\n\n"
            "Please let me know if there's anything else you'd like from me.\n\n"
            "Best regards,\n{candidate_name}"
        ),
    },
    "networking": {
        "subject": "Connecting with you — {candidate_name}",
        "body": (
            "Hi {recipient_name},\n\n"
            "I came across your profile and was impressed by your work at {company}. "
            "I'd love to connect and learn more about your experience in this space.\n\n"
            "Best regards,\n{candidate_name}"
        ),
    },
    "cold_outreach": {
        "subject": "Interested in opportunities at {company}",
        "body": (
            "Hi {recipient_name},\n\n"
            "I'm reaching out because I'm very interested in {company} and believe my background "
            "in {skills_summary} could be a great fit. "
            "Are there any current or upcoming openings you'd recommend I explore?\n\n"
            "Best regards,\n{candidate_name}"
        ),
    },
}

VALID_TYPES = list(EMAIL_TEMPLATES.keys())

# Follow-up schedule: days after the application
FOLLOWUP_SCHEDULE_DAYS = [7, 14]  # 1 week, 2 weeks after application


# ── Template renderer ─────────────────────────────────────────────────────────

def render_template(
    template_key: str,
    context: Dict[str, Any],
) -> Tuple[str, str]:
    """
    Render an email template with context variables.

    Returns (subject, body).
    Raises ValueError if template_key is unknown.
    """
    if template_key not in EMAIL_TEMPLATES:
        raise ValueError(f"Unknown template '{template_key}'. Available: {VALID_TYPES}")

    template = EMAIL_TEMPLATES[template_key]
    subject = template["subject"].format_map(_SafeDict(context))
    body = template["body"].format_map(_SafeDict(context))
    return subject, body


class _SafeDict(dict):
    """Returns '{key}' for missing keys instead of raising KeyError."""
    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"


# ── Service functions ─────────────────────────────────────────────────────────

async def create_email(
    db: AsyncSession,
    candidate: CandidateProfile,
    email_type: str,
    subject: str,
    body_text: str,
    application_id: Optional[uuid.UUID] = None,
    to_address: Optional[str] = None,
    to_name: Optional[str] = None,
    scheduled_at: Optional[datetime] = None,
    template_used: Optional[str] = None,
    is_followup: bool = False,
    followup_number: int = 1,
    parent_email_id: Optional[uuid.UUID] = None,
) -> EmailMessage:
    """Create a draft email message."""
    email = EmailMessage(
        candidate_id=candidate.id,
        application_id=application_id,
        email_type=email_type,
        to_address=to_address,
        to_name=to_name,
        subject=subject,
        body_text=body_text,
        template_used=template_used,
        status="draft" if not scheduled_at else "scheduled",
        scheduled_at=scheduled_at,
        is_followup=is_followup,
        followup_number=followup_number,
        parent_email_id=parent_email_id,
    )
    db.add(email)
    await db.flush()
    await db.refresh(email)
    return email


async def generate_followup_emails(
    db: AsyncSession,
    candidate: CandidateProfile,
    application_id: uuid.UUID,
    job_title: str,
    company: str,
    to_address: Optional[str] = None,
    to_name: Optional[str] = None,
) -> List[EmailMessage]:
    """
    Generate scheduled follow-up emails for an application.

    Creates one email per schedule entry (7 days, 14 days after now).
    """
    now = datetime.now(timezone.utc)
    context = {
        "job_title": job_title,
        "company": company,
        "candidate_name": candidate.full_name or "Candidate",
        "recipient_name": to_name or "Hiring Manager",
    }

    emails = []
    for i, days in enumerate(FOLLOWUP_SCHEDULE_DAYS):
        subject, body = render_template("application_followup", context)
        scheduled = now + timedelta(days=days)
        email = await create_email(
            db=db,
            candidate=candidate,
            email_type="application_followup",
            subject=subject,
            body_text=body,
            application_id=application_id,
            to_address=to_address,
            to_name=to_name,
            scheduled_at=scheduled,
            template_used="application_followup",
            is_followup=(i > 0),
            followup_number=i + 1,
        )
        emails.append(email)

    return emails


async def get_email(db: AsyncSession, email_id: uuid.UUID) -> Optional[EmailMessage]:
    """Fetch a non-deleted email by ID."""
    result = await db.execute(
        select(EmailMessage).where(
            and_(EmailMessage.id == email_id, EmailMessage.deleted_at.is_(None))
        )
    )
    return result.scalar_one_or_none()


async def list_emails(
    db: AsyncSession,
    candidate_id: uuid.UUID,
    email_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[EmailMessage], int]:
    """List emails for a candidate with optional filters."""
    conditions = [
        EmailMessage.candidate_id == candidate_id,
        EmailMessage.deleted_at.is_(None),
    ]
    if email_type:
        conditions.append(EmailMessage.email_type == email_type)
    if status_filter:
        conditions.append(EmailMessage.status == status_filter)

    count_result = await db.execute(
        select(func.count()).select_from(EmailMessage).where(and_(*conditions))
    )
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        select(EmailMessage)
        .where(and_(*conditions))
        .order_by(EmailMessage.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def mark_sent(db: AsyncSession, email_id: uuid.UUID) -> Optional[EmailMessage]:
    """Mark an email as sent."""
    email = await get_email(db, email_id)
    if not email:
        return None
    email.status = "sent"
    email.sent_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(email)
    return email


async def get_due_emails(db: AsyncSession) -> List[EmailMessage]:
    """Return emails that are scheduled and due to be sent now."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(EmailMessage).where(
            and_(
                EmailMessage.status == "scheduled",
                EmailMessage.scheduled_at <= now,
                EmailMessage.deleted_at.is_(None),
            )
        )
    )
    return list(result.scalars().all())


async def delete_email(db: AsyncSession, email_id: uuid.UUID) -> bool:
    """Soft-delete an email."""
    email = await get_email(db, email_id)
    if not email:
        return False
    email.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return True


# ── SMTP sending ──────────────────────────────────────────────────────────────

async def send_email_smtp(
    to_address: str,
    subject: str,
    html_body: str,
    from_address: str | None = None,
) -> bool:
    """
    Send email via SMTP using aiosmtplib.
    Returns True on success, False on failure.
    Falls back gracefully if SMTP not configured (development mode).
    """
    import os
    import logging as _logging

    _logger = _logging.getLogger(__name__)

    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    from_addr = from_address or smtp_user or "noreply@careeros.local"

    if not smtp_host:
        # SMTP not configured — log and skip (development mode)
        _logger.info(
            "SMTP not configured, email not sent",
            extra={"to": to_address, "subject": subject},
        )
        return False

    try:
        import aiosmtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to_address
        msg.attach(MIMEText(html_body, "html"))

        await aiosmtplib.send(
            msg,
            hostname=smtp_host,
            port=smtp_port,
            username=smtp_user or None,
            password=smtp_password or None,
            start_tls=True,
        )
        return True
    except Exception as exc:
        import logging as _logging2
        _logging2.getLogger(__name__).error(f"SMTP send failed: {exc}")
        return False
