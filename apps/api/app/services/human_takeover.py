"""
Human takeover detection for browser automation.

When CareerOS encounters something it cannot safely handle,
it STOPS, records the reason, and waits for human input.

Never bypasses: CAPTCHA, auth challenges, legal questions,
payment requests, security controls.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import re
from typing import Optional


class TakeoverReason(str, Enum):
    CAPTCHA = "captcha"
    AUTH_CHALLENGE = "auth_challenge"
    LEGAL_QUESTION = "legal_question"
    UNKNOWN_FIELD = "unknown_field"
    PAYMENT_REQUEST = "payment_request"
    MISSING_CANDIDATE_INFO = "missing_candidate_info"
    UNEXPECTED_FLOW = "unexpected_flow"
    SECURITY_CHALLENGE = "security_challenge"
    SALARY_NEGOTIATION = "salary_negotiation"


@dataclass
class TakeoverSignal:
    required: bool  # True = must stop
    reason: TakeoverReason
    description: str
    field_name: Optional[str] = None


# Patterns that require human takeover
CAPTCHA_SELECTORS = [
    "iframe[src*='recaptcha']",
    "iframe[src*='hcaptcha']",
    ".g-recaptcha",
    "[data-sitekey]",
    "#cf-challenge-running",
    ".cf-browser-verification",
    "[class*='captcha']",
    "[id*='captcha']",
]

LEGAL_KEYWORDS = [
    r"background check authorization",
    r"criminal record",
    r"drug test consent",
    r"non-compete",
    r"arbitration agreement",
    r"i certify.*information.*true",
    r"e-sign.*agreement",
    r"legal declaration",
]

PAYMENT_KEYWORDS = [
    r"credit card",
    r"payment",
    r"application fee",
    r"processing fee",
]


def detect_captcha_on_page(page_html: str) -> Optional[TakeoverSignal]:
    """Detect CAPTCHA presence from page HTML."""
    patterns = [
        r"recaptcha", r"hcaptcha", r"data-sitekey",
        r"cf-browser-verification", r"cloudflare.*challenge",
    ]
    for pattern in patterns:
        if re.search(pattern, page_html, re.IGNORECASE):
            return TakeoverSignal(
                required=True,
                reason=TakeoverReason.CAPTCHA,
                description="CAPTCHA detected on page. Human action required.",
            )
    return None


def detect_legal_question(field_label: str, field_text: str) -> Optional[TakeoverSignal]:
    """Detect legal/compliance questions that need human review."""
    combined = (field_label + " " + field_text).lower()
    for pattern in LEGAL_KEYWORDS:
        if re.search(pattern, combined):
            return TakeoverSignal(
                required=True,
                reason=TakeoverReason.LEGAL_QUESTION,
                description=f"Legal question detected: '{field_label[:100]}'. Human review required.",
                field_name=field_label,
            )
    return None


def detect_payment_request(page_text: str) -> Optional[TakeoverSignal]:
    """Detect payment requests — always requires human confirmation."""
    for pattern in PAYMENT_KEYWORDS:
        if re.search(pattern, page_text, re.IGNORECASE):
            return TakeoverSignal(
                required=True,
                reason=TakeoverReason.PAYMENT_REQUEST,
                description="Payment request detected. CareerOS never pays on your behalf.",
            )
    return None


def analyze_page_for_takeover(
    page_html: str,
    page_text: str,
    field_labels: Optional[list[str]] = None,
) -> Optional[TakeoverSignal]:
    """
    Comprehensive page analysis for human takeover signals.
    Returns the first (highest priority) signal found, or None.
    """
    # Payment is highest priority — never proceed
    payment = detect_payment_request(page_text)
    if payment:
        return payment

    # CAPTCHA
    captcha = detect_captcha_on_page(page_html)
    if captcha:
        return captcha

    # Legal questions
    for label in (field_labels or []):
        legal = detect_legal_question(label, "")
        if legal:
            return legal

    return None
