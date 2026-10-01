"""CareerOS domain logic — deterministic rules, no LLMs."""
from app.domain.enums import (
    EvidenceStrength,
    FactCategory,
    EvidenceSourceType,
    EvidenceStatus,
    GapType,
    RemoteType,
    EmploymentType,
    WorkAuthorization,
)
from app.domain.evidence import (
    validate_evidence,
    can_claim_be_used,
    requires_human_review,
    classify_gap,
    EvidenceValidationResult,
)

__all__ = [
    "EvidenceStrength",
    "FactCategory",
    "EvidenceSourceType",
    "EvidenceStatus",
    "GapType",
    "RemoteType",
    "EmploymentType",
    "WorkAuthorization",
    "validate_evidence",
    "can_claim_be_used",
    "requires_human_review",
    "classify_gap",
    "EvidenceValidationResult",
]
