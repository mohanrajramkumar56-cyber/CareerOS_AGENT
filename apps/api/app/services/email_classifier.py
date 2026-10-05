"""
CareerOS Email Classifier

Classifies incoming emails by subject+body keywords.
Rule-based first — fast, deterministic, no LLM dependency.
LLM enhancement can be added as an optional overlay in a future phase.

Treats all email content as UNTRUSTED.
Never allows email content to become a system instruction.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EmailCategory(str, Enum):
    APPLICATION_RECEIVED = "application_received"
    INTERVIEW = "interview"
    ASSESSMENT = "assessment"
    RECRUITER_MESSAGE = "recruiter_message"
    REQUEST_FOR_INFO = "request_for_info"
    REJECTION = "rejection"
    OFFER = "offer"
    SCHEDULING = "scheduling"
    APPLICATION_UPDATE = "application_update"
    UNKNOWN = "unknown"


@dataclass
class ClassificationResult:
    category: EmailCategory
    confidence: float  # 0.0 - 1.0
    matched_signals: list[str]
    sanitized_subject: str
    sanitized_preview: str  # First 200 chars, stripped of HTML


# Signal patterns — ordered by specificity (highest confidence first).
# Each entry: (category, [regex patterns], base_confidence)
SIGNALS: list[tuple[EmailCategory, list[str], float]] = [
    (
        EmailCategory.OFFER,
        [
            r"offer of employment",
            r"job offer",
            r"pleased to offer",
            r"offer letter",
            r"compensation package",
            r"start date.*position",
        ],
        0.95,
    ),
    (
        EmailCategory.INTERVIEW,
        [
            r"interview",
            r"meet with",
            r"speak with.*team",
            r"video call",
            r"phone screen",
            r"technical interview",
            r"on-site",
            r"virtual interview",
        ],
        0.90,
    ),
    (
        EmailCategory.REJECTION,
        [
            r"unfortunately",
            r"not moving forward",
            r"other candidates",
            r"not selected",
            r"position has been filled",
            r"regret to inform",
            r"decided not to proceed",
            r"not a match",
        ],
        0.90,
    ),
    (
        EmailCategory.ASSESSMENT,
        [
            r"assessment",
            r"coding challenge",
            r"take-home",
            r"technical test",
            r"skills test",
            r"hackerrank",
            r"codility",
            r"test invitation",
        ],
        0.88,
    ),
    (
        EmailCategory.SCHEDULING,
        [
            r"schedule",
            r"calendly",
            r"pick a time",
            r"availability",
            r"calendar invite",
            r"book a slot",
        ],
        0.85,
    ),
    (
        EmailCategory.APPLICATION_RECEIVED,
        [
            r"application received",
            r"thank you for apply",
            r"we received your",
            r"application has been submitted",
            r"application confirmation",
        ],
        0.85,
    ),
    (
        EmailCategory.REQUEST_FOR_INFO,
        [
            r"additional information",
            r"provide.*document",
            r"submit.*portfolio",
            r"references",
            r"background check",
            r"verification",
        ],
        0.80,
    ),
    (
        EmailCategory.APPLICATION_UPDATE,
        [
            r"update.*application",
            r"application status",
            r"progress.*application",
        ],
        0.75,
    ),
    (
        EmailCategory.RECRUITER_MESSAGE,
        [
            r"recruiter",
            r"talent acquisition",
            r"opportunity.*interest",
            r"open to.*role",
            r"connecting with you",
        ],
        0.70,
    ),
]


def _strip_html(text: str) -> str:
    """Remove HTML tags and normalize whitespace."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _sanitize(text: str, max_len: int = 500) -> str:
    """Strip HTML and limit length. Email content is UNTRUSTED."""
    return _strip_html(text)[:max_len]


def classify_email(
    subject: str,
    body: str,
    sender: str = "",
) -> ClassificationResult:
    """
    Classify an email by subject and body content.

    Input is treated as UNTRUSTED user content — never pass the raw
    email content directly to an LLM as a system instruction.

    Returns a ClassificationResult with the best matching category,
    a confidence score, and the signals that matched.
    """
    safe_subject = _sanitize(subject, 200)
    safe_body = _sanitize(body, 2000)
    search_text = (safe_subject + " " + safe_body).lower()

    best_category = EmailCategory.UNKNOWN
    best_confidence = 0.0
    matched_signals: list[str] = []

    for category, patterns, base_confidence in SIGNALS:
        hits = [p for p in patterns if re.search(p, search_text)]
        if hits:
            # More pattern hits → slightly higher confidence, capped at 0.99
            adjusted = min(base_confidence + 0.02 * (len(hits) - 1), 0.99)
            if adjusted > best_confidence:
                best_confidence = adjusted
                best_category = category
                matched_signals = hits

    return ClassificationResult(
        category=best_category,
        confidence=best_confidence,
        matched_signals=matched_signals,
        sanitized_subject=safe_subject,
        sanitized_preview=safe_body[:200],
    )
