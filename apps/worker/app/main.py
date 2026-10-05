"""
CareerOS Worker — ARQ background task runner.

Workers:
- run_matching: Match a candidate against a job
- generate_resume: Generate a tailored resume
- process_email: Classify and correlate an incoming email
- send_followup_email: Send a scheduled follow-up email

The worker imports from the API app by injecting the API path into sys.path.
"""
from __future__ import annotations

import logging
import os
import sys

# Add the API app directory to the Python path so we can import from `app.*`
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "api"),
)

logger = logging.getLogger(__name__)


# ── Lifecycle ─────────────────────────────────────────────────────────────────

async def startup(ctx: dict) -> None:
    """Worker startup: stash db session factory in context."""
    from app.db.session import async_session_factory  # noqa: PLC0415

    ctx["db_factory"] = async_session_factory
    logger.info("CareerOS worker started")


async def shutdown(ctx: dict) -> None:
    """Worker shutdown: nothing to clean up (sessions are per-task)."""
    logger.info("CareerOS worker stopped")


# ── Tasks ─────────────────────────────────────────────────────────────────────

async def run_matching(ctx: dict, *, candidate_id: str, job_id: str) -> dict:
    """Match a candidate against a job using the matching service."""
    try:
        import uuid  # noqa: PLC0415

        from app.db.session import async_session_factory  # noqa: PLC0415
        from app.services.matching import MatchingService  # noqa: PLC0415

        async with async_session_factory() as db:
            svc = MatchingService(db)
            result = await svc.compute_match(
                candidate_id=uuid.UUID(candidate_id),
                job_id=uuid.UUID(job_id),
            )
            return {
                "status": "ok",
                "match_id": str(result.id) if result else None,
            }
    except Exception as exc:
        logger.exception("run_matching failed: %s", exc)
        return {"status": "error", "error": str(exc)}


async def generate_resume(
    ctx: dict,
    *,
    candidate_id: str,
    job_id: str | None = None,
    template: str = "standard",
) -> dict:
    """Generate a tailored resume for a candidate."""
    try:
        import uuid  # noqa: PLC0415

        from app.db.session import async_session_factory  # noqa: PLC0415
        from app.services.resume_builder import ResumeBuilder  # noqa: PLC0415

        async with async_session_factory() as db:
            builder = ResumeBuilder(db)
            resume = await builder.generate(
                candidate_id=uuid.UUID(candidate_id),
                job_id=uuid.UUID(job_id) if job_id else None,
                template=template,
            )
            return {"status": "ok", "resume_id": str(resume.id)}
    except Exception as exc:
        logger.exception("generate_resume failed: %s", exc)
        return {"status": "error", "error": str(exc)}


async def process_email(ctx: dict, *, email_id: str) -> dict:
    """
    Classify and correlate an incoming email.

    Loads the EmailMessage by ID, runs the rule-based classifier,
    and persists the classification result back to the database.
    """
    try:
        import uuid  # noqa: PLC0415

        from sqlalchemy import select  # noqa: PLC0415

        from app.db.session import async_session_factory  # noqa: PLC0415
        from app.models.email_message import EmailMessage  # noqa: PLC0415
        from app.services.email_classifier import classify_email  # noqa: PLC0415

        async with async_session_factory() as db:
            result = await db.execute(
                select(EmailMessage).where(
                    EmailMessage.id == uuid.UUID(email_id)
                )
            )
            email = result.scalar_one_or_none()
            if not email:
                return {"status": "error", "error": "Email not found"}

            classification = classify_email(
                subject=email.subject or "",
                body=email.body_text or email.body_html or "",
            )
            email.classification = classification.category.value
            email.classification_confidence = classification.confidence
            await db.commit()

            return {
                "status": "ok",
                "category": classification.category.value,
                "confidence": classification.confidence,
            }
    except Exception as exc:
        logger.exception("process_email failed: %s", exc)
        return {"status": "error", "error": str(exc)}


async def send_followup_email(ctx: dict, *, email_id: str) -> dict:
    """
    Send a scheduled follow-up email via SMTP.

    Loads the EmailMessage, sends it, then updates its status to
    'sent' or 'failed' depending on the outcome.
    """
    try:
        import uuid  # noqa: PLC0415
        from datetime import datetime, timezone  # noqa: PLC0415

        from sqlalchemy import select  # noqa: PLC0415

        from app.db.session import async_session_factory  # noqa: PLC0415
        from app.models.email_message import EmailMessage  # noqa: PLC0415
        from app.services.email_service import send_email_smtp  # noqa: PLC0415

        async with async_session_factory() as db:
            result = await db.execute(
                select(EmailMessage).where(
                    EmailMessage.id == uuid.UUID(email_id)
                )
            )
            email = result.scalar_one_or_none()
            if not email:
                return {"status": "error", "error": "Email not found"}

            if email.status == "sent":
                return {"status": "skipped", "reason": "already sent"}

            if not email.to_address:
                email.status = "failed"
                email.send_error = "No recipient address"
                await db.commit()
                return {"status": "failed", "reason": "no recipient address"}

            success = await send_email_smtp(
                to_address=email.to_address,
                subject=email.subject or "Follow-up",
                html_body=email.body_html or email.body_text or "",
            )
            if success:
                email.status = "sent"
                email.sent_at = datetime.now(timezone.utc)
            else:
                email.status = "failed"
                email.send_error = "SMTP send returned False"

            await db.commit()
            return {"status": "ok" if success else "failed"}
    except Exception as exc:
        logger.exception("send_followup_email failed: %s", exc)
        return {"status": "error", "error": str(exc)}


# ── ARQ WorkerSettings ────────────────────────────────────────────────────────

class WorkerSettings:
    functions = [
        run_matching,
        generate_resume,
        process_email,
        send_followup_email,
    ]
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 4
    job_timeout = 300  # seconds


if __name__ == "__main__":
    import arq

    arq.run_worker(WorkerSettings)
