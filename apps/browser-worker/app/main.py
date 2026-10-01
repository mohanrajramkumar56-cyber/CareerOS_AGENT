"""
CareerOS Browser Worker — Playwright-based controlled application automation.

Responsibilities:
- Manage isolated browser sessions per application
- Execute form-filling automation
- Detect human takeover triggers (CAPTCHA, unknown questions)
- Pause and notify candidate when human intervention required
- Record screenshots and page state for audit

Phase 0: Skeleton only. Full implementation in Phase 5.
"""
import logging

logger = logging.getLogger(__name__)


async def start_browser_session(ctx: dict, *, session_id: str) -> dict:
    """Start a controlled browser session for an application."""
    raise NotImplementedError("Phase 5: Application Engine")


async def resume_browser_session(ctx: dict, *, session_id: str) -> dict:
    """Resume a paused browser session after human approval."""
    raise NotImplementedError("Phase 5: Application Engine")


async def fill_application_form(
    ctx: dict, *, session_id: str, field_answers: dict
) -> dict:
    """Fill application form fields using verified candidate evidence."""
    raise NotImplementedError("Phase 5: Application Engine")


class BrowserWorkerSettings:
    functions = [
        start_browser_session,
        resume_browser_session,
        fill_application_form,
    ]
    max_jobs = 2  # Browser automation is resource-intensive
    job_timeout = 600  # 10 minutes per application session
