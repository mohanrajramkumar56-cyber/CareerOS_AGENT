"""
CareerOS - Candidate Intelligence Domain Enums and Core Logic.

Truth policy: every candidate claim must have traceable evidence.
UNKNOWN is used when evidence is absent — never ASSUMED or GENERATED.
"""
from __future__ import annotations

from enum import Enum


class EvidenceStrength(str, Enum):
    """
    How strongly the evidence supports a candidate claim.

    VERIFIED   – externally verifiable (certificate URL, GitHub commit, etc.)
    STRONG     – multi-source or detailed self-reported with specifics
    MODERATE   – single-source self-reported, plausible
    WEAK       – vague self-report, low detail
    UNKNOWN    – no evidence; the fact MUST NOT be asserted in applications
    """
    VERIFIED = "verified"
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    UNKNOWN = "unknown"


class FactCategory(str, Enum):
    """Category of a candidate fact in the evidence graph."""
    SKILL = "skill"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    PROJECT = "project"
    CERTIFICATION = "certification"
    ACHIEVEMENT = "achievement"
    TECHNOLOGY = "technology"
    RESPONSIBILITY = "responsibility"
    LANGUAGE = "language"
    PUBLICATION = "publication"
    VOLUNTEER = "volunteer"


class EvidenceSourceType(str, Enum):
    """Where the evidence came from."""
    RESUME = "resume"
    WORK_HISTORY = "work_history"
    PROJECT = "project"
    GIT_REPOSITORY = "git_repository"
    PORTFOLIO = "portfolio"
    CERTIFICATE = "certificate"
    UPLOADED_DOCUMENT = "uploaded_document"
    USER_CONFIRMATION = "user_confirmation"
    LINKEDIN = "linkedin"
    GITHUB = "github"
    EXTERNAL_LINK = "external_link"


class EvidenceStatus(str, Enum):
    """Verification status of a piece of evidence."""
    UNVERIFIED = "unverified"     # Not yet checked
    VERIFIED = "verified"         # Externally confirmed
    DISPUTED = "disputed"         # Cannot be confirmed
    EXPIRED = "expired"           # Was valid, now outdated


class GapType(str, Enum):
    """
    Classification of a gap identified during matching.

    SKILL_GAP           – candidate has no evidence for this skill
    REPRESENTATION_GAP  – candidate has evidence but resume doesn't show it
    """
    SKILL_GAP = "skill_gap"
    REPRESENTATION_GAP = "representation_gap"


class RemoteType(str, Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    UNSPECIFIED = "unspecified"


class EmploymentType(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    FREELANCE = "freelance"
    INTERNSHIP = "internship"
    UNSPECIFIED = "unspecified"


class WorkAuthorization(str, Enum):
    CITIZEN = "citizen"
    PERMANENT_RESIDENT = "permanent_resident"
    WORK_VISA = "work_visa"
    REQUIRES_SPONSORSHIP = "requires_sponsorship"
    NOT_DISCLOSED = "not_disclosed"
