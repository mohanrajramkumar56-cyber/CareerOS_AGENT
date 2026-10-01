"""
CareerOS - Evidence validation domain logic.

Core truth-policy rules:
1. A claim with EvidenceStrength.UNKNOWN must never appear in a resume or application.
2. A WEAK claim may appear in a resume but must be flagged.
3. Evidence must always have a source type.
4. A candidate fact with no linked evidence defaults to UNKNOWN.

These rules are deterministic — no LLM involvement.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from app.domain.enums import EvidenceStrength, FactCategory, EvidenceSourceType


@dataclass(frozen=True)
class EvidenceValidationResult:
    """Result of validating a piece of evidence."""
    is_valid: bool
    strength: EvidenceStrength
    errors: List[str]
    warnings: List[str]

    @property
    def can_be_used_in_resume(self) -> bool:
        """True if evidence is strong enough to include in a resume."""
        return self.is_valid and self.strength not in (EvidenceStrength.UNKNOWN,)

    @property
    def can_be_auto_filled(self) -> bool:
        """True if evidence is strong enough for automated form filling."""
        return self.is_valid and self.strength in (
            EvidenceStrength.VERIFIED,
            EvidenceStrength.STRONG,
        )


def validate_evidence(
    claim: str,
    category: FactCategory,
    source_type: Optional[EvidenceSourceType],
    source_reference: Optional[str],
    normalized_value: Optional[str],
) -> EvidenceValidationResult:
    """
    Validate a candidate evidence entry against CareerOS truth policy.

    Returns a structured validation result with strength assessment.
    This function is deterministic — no AI involvement.
    """
    errors: List[str] = []
    warnings: List[str] = []

    # Rule 1: claim must not be empty
    if not claim or not claim.strip():
        errors.append("Evidence claim must not be empty")

    # Rule 2: source type must be specified
    if source_type is None:
        errors.append("Evidence must have a source type")
        return EvidenceValidationResult(
            is_valid=False,
            strength=EvidenceStrength.UNKNOWN,
            errors=errors,
            warnings=warnings,
        )

    # Rule 3: compute strength based on source quality
    strength = _compute_strength(
        source_type=source_type,
        source_reference=source_reference,
        normalized_value=normalized_value,
        category=category,
    )

    # Rule 4: warn on weak evidence
    if strength == EvidenceStrength.WEAK:
        warnings.append(
            f"Evidence for '{claim}' is weak — consider adding a verifiable source"
        )

    if strength == EvidenceStrength.UNKNOWN:
        errors.append(
            f"Evidence for '{claim}' has no source — this claim cannot be used in resumes or applications"
        )

    is_valid = len(errors) == 0

    return EvidenceValidationResult(
        is_valid=is_valid,
        strength=strength,
        errors=errors,
        warnings=warnings,
    )


def _compute_strength(
    source_type: EvidenceSourceType,
    source_reference: Optional[str],
    normalized_value: Optional[str],
    category: FactCategory,
) -> EvidenceStrength:
    """
    Compute evidence strength from its source type and reference quality.

    Hierarchy:
    - Externally verifiable sources (cert URL, GitHub, portfolio) → VERIFIED
    - Structured uploaded document + reference → STRONG
    - Self-report with specific reference → MODERATE
    - Self-report with no reference → WEAK
    """
    has_reference = bool(source_reference and source_reference.strip())
    has_normalized = bool(normalized_value and normalized_value.strip())

    # Externally verifiable sources
    if source_type in (
        EvidenceSourceType.GIT_REPOSITORY,
        EvidenceSourceType.CERTIFICATE,
        EvidenceSourceType.GITHUB,
        EvidenceSourceType.LINKEDIN,
        EvidenceSourceType.EXTERNAL_LINK,
        EvidenceSourceType.PORTFOLIO,
    ):
        if has_reference:
            return EvidenceStrength.VERIFIED
        return EvidenceStrength.STRONG  # source type is good but no URL yet

    # Structured document sources
    if source_type in (
        EvidenceSourceType.UPLOADED_DOCUMENT,
        EvidenceSourceType.RESUME,
    ):
        if has_reference and has_normalized:
            return EvidenceStrength.STRONG
        if has_reference or has_normalized:
            return EvidenceStrength.MODERATE
        return EvidenceStrength.WEAK

    # Work history and project — strong if properly referenced
    if source_type in (
        EvidenceSourceType.WORK_HISTORY,
        EvidenceSourceType.PROJECT,
    ):
        if has_reference and has_normalized:
            return EvidenceStrength.STRONG
        if has_reference:
            return EvidenceStrength.MODERATE
        return EvidenceStrength.WEAK

    # User confirmation only — weakest credible source
    if source_type == EvidenceSourceType.USER_CONFIRMATION:
        if has_normalized:
            return EvidenceStrength.MODERATE
        return EvidenceStrength.WEAK

    return EvidenceStrength.UNKNOWN


def can_claim_be_used(strength: EvidenceStrength) -> bool:
    """Returns True if a claim at this evidence strength can appear in a resume."""
    return strength not in (EvidenceStrength.UNKNOWN,)


def requires_human_review(strength: EvidenceStrength) -> bool:
    """Returns True if the claim should be reviewed by the candidate before use."""
    return strength in (EvidenceStrength.WEAK,)


def classify_gap(
    has_evidence: bool,
    represented_in_resume: bool,
) -> Optional[str]:
    """
    Classify the type of gap for a skill/fact.

    Returns:
        'skill_gap'           – no evidence exists
        'representation_gap'  – evidence exists but not in resume
        None                  – no gap
    """
    if not has_evidence:
        return "skill_gap"
    if has_evidence and not represented_in_resume:
        return "representation_gap"
    return None
