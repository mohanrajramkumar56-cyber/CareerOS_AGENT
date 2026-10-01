"""
Unit tests for CareerOS evidence domain logic.

Tests the truth-policy enforcement:
- EvidenceStrength computation
- validate_evidence rules
- can_claim_be_used / requires_human_review
- classify_gap
- _aggregate_strength
"""
from __future__ import annotations

import pytest

from app.domain.enums import (
    EvidenceSourceType,
    EvidenceStrength,
    FactCategory,
)
from app.domain.evidence import (
    EvidenceValidationResult,
    _compute_strength,
    can_claim_be_used,
    classify_gap,
    requires_human_review,
    validate_evidence,
)
from app.services.candidate import _aggregate_strength


class TestEvidenceStrengthEnum:
    def test_all_values_exist(self):
        assert EvidenceStrength.VERIFIED
        assert EvidenceStrength.STRONG
        assert EvidenceStrength.MODERATE
        assert EvidenceStrength.WEAK
        assert EvidenceStrength.UNKNOWN

    def test_string_values(self):
        assert EvidenceStrength.VERIFIED.value == "verified"
        assert EvidenceStrength.UNKNOWN.value == "unknown"


class TestFactCategoryEnum:
    def test_skill_category(self):
        assert FactCategory.SKILL.value == "skill"

    def test_all_categories_exist(self):
        categories = [
            "skill", "experience", "education", "project",
            "certification", "achievement", "technology",
            "responsibility", "language", "publication", "volunteer"
        ]
        for cat in categories:
            assert FactCategory(cat) is not None


class TestComputeStrength:
    """Tests for _compute_strength (internal function)."""

    def test_github_with_reference_is_verified(self):
        result = _compute_strength(
            source_type=EvidenceSourceType.GITHUB,
            source_reference="https://github.com/user/repo",
            normalized_value="Python",
            category=FactCategory.SKILL,
        )
        assert result == EvidenceStrength.VERIFIED

    def test_certificate_with_url_is_verified(self):
        result = _compute_strength(
            source_type=EvidenceSourceType.CERTIFICATE,
            source_reference="https://cert.example.com/abc123",
            normalized_value="AWS Certified",
            category=FactCategory.CERTIFICATION,
        )
        assert result == EvidenceStrength.VERIFIED

    def test_external_link_without_reference_is_strong(self):
        result = _compute_strength(
            source_type=EvidenceSourceType.EXTERNAL_LINK,
            source_reference=None,
            normalized_value=None,
            category=FactCategory.PROJECT,
        )
        assert result == EvidenceStrength.STRONG

    def test_resume_with_full_details_is_strong(self):
        result = _compute_strength(
            source_type=EvidenceSourceType.RESUME,
            source_reference="resume_v3.pdf",
            normalized_value="Software Engineer",
            category=FactCategory.EXPERIENCE,
        )
        assert result == EvidenceStrength.STRONG

    def test_resume_with_only_reference_is_moderate(self):
        result = _compute_strength(
            source_type=EvidenceSourceType.RESUME,
            source_reference="resume.pdf",
            normalized_value=None,
            category=FactCategory.EXPERIENCE,
        )
        assert result == EvidenceStrength.MODERATE

    def test_resume_with_nothing_is_weak(self):
        result = _compute_strength(
            source_type=EvidenceSourceType.RESUME,
            source_reference=None,
            normalized_value=None,
            category=FactCategory.SKILL,
        )
        assert result == EvidenceStrength.WEAK

    def test_work_history_with_reference_is_moderate(self):
        result = _compute_strength(
            source_type=EvidenceSourceType.WORK_HISTORY,
            source_reference="Acme Corp 2020-2023",
            normalized_value=None,
            category=FactCategory.EXPERIENCE,
        )
        assert result == EvidenceStrength.MODERATE

    def test_user_confirmation_with_normalized_is_moderate(self):
        result = _compute_strength(
            source_type=EvidenceSourceType.USER_CONFIRMATION,
            source_reference=None,
            normalized_value="Python",
            category=FactCategory.SKILL,
        )
        assert result == EvidenceStrength.MODERATE

    def test_user_confirmation_bare_is_weak(self):
        result = _compute_strength(
            source_type=EvidenceSourceType.USER_CONFIRMATION,
            source_reference=None,
            normalized_value=None,
            category=FactCategory.SKILL,
        )
        assert result == EvidenceStrength.WEAK


class TestValidateEvidence:
    """Tests for the main validate_evidence function."""

    def test_empty_claim_is_invalid(self):
        result = validate_evidence(
            claim="",
            category=FactCategory.SKILL,
            source_type=EvidenceSourceType.GITHUB,
            source_reference="https://github.com/u/r",
            normalized_value="Python",
        )
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_no_source_type_is_invalid(self):
        result = validate_evidence(
            claim="Knows Python",
            category=FactCategory.SKILL,
            source_type=None,
            source_reference=None,
            normalized_value=None,
        )
        assert result.is_valid is False
        assert result.strength == EvidenceStrength.UNKNOWN

    def test_verified_evidence_is_valid_and_usable(self):
        result = validate_evidence(
            claim="AWS Certified Solutions Architect",
            category=FactCategory.CERTIFICATION,
            source_type=EvidenceSourceType.CERTIFICATE,
            source_reference="https://aws.amazon.com/verify/abc123",
            normalized_value="AWS-SAA",
        )
        assert result.is_valid is True
        assert result.strength == EvidenceStrength.VERIFIED
        assert result.can_be_used_in_resume is True
        assert result.can_be_auto_filled is True
        assert len(result.errors) == 0

    def test_weak_evidence_generates_warning(self):
        result = validate_evidence(
            claim="I know some Python",
            category=FactCategory.SKILL,
            source_type=EvidenceSourceType.USER_CONFIRMATION,
            source_reference=None,
            normalized_value=None,
        )
        assert result.is_valid is True
        assert result.strength == EvidenceStrength.WEAK
        assert len(result.warnings) > 0
        assert result.can_be_used_in_resume is True  # weak but not unknown
        assert result.can_be_auto_filled is False  # too weak for auto-fill

    def test_unknown_strength_cannot_be_used_in_resume(self):
        result = validate_evidence(
            claim="I might know Kubernetes",
            category=FactCategory.SKILL,
            source_type=None,
            source_reference=None,
            normalized_value=None,
        )
        assert result.can_be_used_in_resume is False

    def test_strong_evidence_can_be_auto_filled(self):
        result = validate_evidence(
            claim="Led backend team",
            category=FactCategory.EXPERIENCE,
            source_type=EvidenceSourceType.WORK_HISTORY,
            source_reference="Acme Corp",
            normalized_value="Tech Lead",
        )
        assert result.is_valid is True
        assert result.strength == EvidenceStrength.STRONG
        assert result.can_be_auto_filled is True


class TestCanClaimBeUsed:
    def test_verified_can_be_used(self):
        assert can_claim_be_used(EvidenceStrength.VERIFIED) is True

    def test_strong_can_be_used(self):
        assert can_claim_be_used(EvidenceStrength.STRONG) is True

    def test_moderate_can_be_used(self):
        assert can_claim_be_used(EvidenceStrength.MODERATE) is True

    def test_weak_can_be_used(self):
        assert can_claim_be_used(EvidenceStrength.WEAK) is True

    def test_unknown_cannot_be_used(self):
        assert can_claim_be_used(EvidenceStrength.UNKNOWN) is False


class TestRequiresHumanReview:
    def test_weak_requires_review(self):
        assert requires_human_review(EvidenceStrength.WEAK) is True

    def test_verified_does_not_require_review(self):
        assert requires_human_review(EvidenceStrength.VERIFIED) is False

    def test_strong_does_not_require_review(self):
        assert requires_human_review(EvidenceStrength.STRONG) is False

    def test_unknown_does_not_require_review(self):
        # Unknown is blocked entirely — separate from requiring review
        assert requires_human_review(EvidenceStrength.UNKNOWN) is False


class TestClassifyGap:
    def test_no_evidence_is_skill_gap(self):
        gap = classify_gap(has_evidence=False, represented_in_resume=False)
        assert gap == "skill_gap"

    def test_evidence_but_not_in_resume_is_representation_gap(self):
        gap = classify_gap(has_evidence=True, represented_in_resume=False)
        assert gap == "representation_gap"

    def test_evidence_and_in_resume_is_no_gap(self):
        gap = classify_gap(has_evidence=True, represented_in_resume=True)
        assert gap is None

    def test_no_evidence_in_resume_is_skill_gap(self):
        # Edge: someone put it in resume with no evidence — still a skill gap
        gap = classify_gap(has_evidence=False, represented_in_resume=True)
        assert gap == "skill_gap"


class TestAggregateStrength:
    def test_empty_list_is_unknown(self):
        result = _aggregate_strength([])
        assert result == EvidenceStrength.UNKNOWN

    def test_single_verified_is_verified(self):
        result = _aggregate_strength([EvidenceStrength.VERIFIED])
        assert result == EvidenceStrength.VERIFIED

    def test_mixed_returns_strongest(self):
        result = _aggregate_strength([
            EvidenceStrength.WEAK,
            EvidenceStrength.MODERATE,
            EvidenceStrength.STRONG,
        ])
        assert result == EvidenceStrength.STRONG

    def test_all_unknown_is_unknown(self):
        result = _aggregate_strength([
            EvidenceStrength.UNKNOWN,
            EvidenceStrength.UNKNOWN,
        ])
        assert result == EvidenceStrength.UNKNOWN

    def test_one_verified_among_weak_is_verified(self):
        result = _aggregate_strength([
            EvidenceStrength.WEAK,
            EvidenceStrength.VERIFIED,
            EvidenceStrength.UNKNOWN,
        ])
        assert result == EvidenceStrength.VERIFIED
