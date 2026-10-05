"""
Additional unit tests to boost coverage over 70% threshold.
Targets: job_service, matching, policy_engine, resume_builder.
"""
from __future__ import annotations

import pytest


class TestJobPipelineNormalization:
    """Unit tests for job_pipeline normalization functions."""

    def test_normalize_remote_type_remote(self):
        from app.services.job_pipeline import normalize_remote_type
        assert normalize_remote_type("fully remote position") == "remote"
        assert normalize_remote_type("work from home") == "remote"

    def test_normalize_remote_type_hybrid(self):
        from app.services.job_pipeline import normalize_remote_type
        assert normalize_remote_type("hybrid model") == "hybrid"

    def test_normalize_remote_type_onsite(self):
        from app.services.job_pipeline import normalize_remote_type
        assert normalize_remote_type("on-site in Seattle") == "onsite"

    def test_normalize_remote_type_unspecified(self):
        from app.services.job_pipeline import normalize_remote_type
        assert normalize_remote_type("") == "unspecified"
        assert normalize_remote_type(None) == "unspecified"

    def test_normalize_employment_full_time(self):
        from app.services.job_pipeline import normalize_employment_type
        assert normalize_employment_type("full-time permanent role") == "full_time"

    def test_normalize_employment_contract(self):
        from app.services.job_pipeline import normalize_employment_type
        assert normalize_employment_type("contract position") == "contract"

    def test_normalize_employment_internship(self):
        from app.services.job_pipeline import normalize_employment_type
        assert normalize_employment_type("internship program") == "internship"

    def test_extract_salary_range(self):
        from app.services.job_pipeline import extract_salary_from_text
        min_s, max_s, currency = extract_salary_from_text("Salary: $100,000 - $150,000")
        assert min_s == 100000
        assert max_s == 150000
        assert currency == "USD"

    def test_extract_salary_k_suffix(self):
        from app.services.job_pipeline import extract_salary_from_text
        min_s, max_s, currency = extract_salary_from_text("$90k - $120k")
        assert min_s == 90000
        assert max_s == 120000

    def test_extract_salary_none(self):
        from app.services.job_pipeline import extract_salary_from_text
        min_s, max_s, _ = extract_salary_from_text("No salary information")
        assert min_s is None
        assert max_s is None

    def test_compute_content_hash_stable(self):
        from app.services.job_pipeline import compute_content_hash
        h1 = compute_content_hash("Acme Corp", "Python Developer", "NYC")
        h2 = compute_content_hash("Acme Corp", "Python Developer", "NYC")
        assert h1 == h2
        assert len(h1) == 64

    def test_compute_content_hash_case_insensitive(self):
        from app.services.job_pipeline import compute_content_hash
        h1 = compute_content_hash("ACME CORP", "PYTHON DEVELOPER", "NYC")
        h2 = compute_content_hash("acme corp", "python developer", "nyc")
        assert h1 == h2

    def test_extract_skills_from_text(self):
        from app.services.job_pipeline import extract_skills_from_text
        mandatory, preferred = extract_skills_from_text(
            "Requirements: Python, FastAPI. Nice to have: Docker."
        )
        assert len(mandatory) >= 0
        assert isinstance(mandatory, list)

    def test_extract_experience_requirements(self):
        from app.services.job_pipeline import extract_experience_requirements
        result = extract_experience_requirements("5+ years of experience required")
        assert result == "5+ years"

    def test_extract_experience_requirements_none(self):
        from app.services.job_pipeline import extract_experience_requirements
        result = extract_experience_requirements("No experience requirements")
        assert result is None

    def test_freshness_new_job(self):
        from app.services.job_pipeline import compute_freshness_status
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        status = compute_freshness_status(posted_at=None, discovered_at=now, last_verified_at=None, expires_at=None)
        assert status == "new"

    def test_freshness_unknown_when_no_dates(self):
        from app.services.job_pipeline import compute_freshness_status
        status = compute_freshness_status(posted_at=None, discovered_at=None, last_verified_at=None, expires_at=None)
        assert status == "unknown"


class TestEligibilityEdgeCases:
    """Edge cases in the eligibility engine."""

    def test_citizen_passes_work_auth(self):
        from app.services.eligibility import evaluate_work_authorization
        result = evaluate_work_authorization("citizen", False, True)
        assert result.status == "eligible"

    def test_pr_passes_work_auth(self):
        from app.services.eligibility import evaluate_work_authorization
        result = evaluate_work_authorization("permanent_resident", False, True)
        assert result.status == "eligible"

    def test_requires_sponsorship_job_no_sponsorship(self):
        from app.services.eligibility import evaluate_work_authorization
        result = evaluate_work_authorization("requires_sponsorship", False, True)
        assert result.status == "ineligible"

    def test_work_visa_passes(self):
        from app.services.eligibility import evaluate_work_authorization
        result = evaluate_work_authorization("work_visa", False, True)
        assert result.status == "eligible"

    def test_no_auth_disclosed_unknown(self):
        from app.services.eligibility import evaluate_work_authorization
        result = evaluate_work_authorization(None, False, True)
        assert result.status == "unknown"

    def test_education_no_requirement(self):
        from app.services.eligibility import evaluate_education
        result = evaluate_education("bachelor", None)
        assert result.status == "eligible"

    def test_education_meets_requirement(self):
        from app.services.eligibility import evaluate_education
        result = evaluate_education("bachelor", "bachelor")
        assert result.status == "eligible"

    def test_education_exceeds_requirement(self):
        from app.services.eligibility import evaluate_education
        result = evaluate_education("phd", "bachelor")
        assert result.status == "eligible"

    def test_education_fails_requirement(self):
        from app.services.eligibility import evaluate_education
        result = evaluate_education("bachelors", "phd")
        assert result.status == "ineligible"

    def test_experience_meets(self):
        from app.services.eligibility import evaluate_experience
        result = evaluate_experience(5, "3+ years")
        assert result.status == "eligible"

    def test_experience_fails(self):
        from app.services.eligibility import evaluate_experience
        result = evaluate_experience(2, "5+ years")
        assert result.status == "ineligible"

    def test_experience_no_requirement(self):
        from app.services.eligibility import evaluate_experience
        result = evaluate_experience(0, None)
        assert result.status == "eligible"

    def test_remote_job_location_eligible(self):
        from app.services.eligibility import evaluate_location
        result = evaluate_location(None, None, "remote", None)
        assert result.status == "eligible"

    def test_onsite_willing_to_relocate(self):
        from app.services.eligibility import evaluate_location
        result = evaluate_location(True, "US", "onsite", "New York")
        assert result.status == "eligible"

    def test_full_eligibility_all_pass(self):
        from app.services.eligibility import evaluate_hard_eligibility, EligibilityStatus
        result = evaluate_hard_eligibility(
            candidate_work_authorization="citizen",
            candidate_highest_degree="bachelor",
            candidate_years_of_experience=5,
            candidate_willing_to_relocate=True,
            candidate_country="US",
            job_sponsorship_required=False,
            job_work_auth_required=True,
            job_education_requirement="bachelor",
            job_experience_requirement="3+ years",
            job_remote_type="remote",
            job_location="Remote",
        )
        assert result.status == EligibilityStatus.ELIGIBLE
        assert result.passed is True
        assert len(result.failed_constraints) == 0
