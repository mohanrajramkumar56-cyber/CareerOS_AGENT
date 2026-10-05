"""
CareerOS - Hard Eligibility Engine.

Evaluates hard constraints between a job and a candidate.

Critical architecture principle:
- Hard eligibility is DETERMINISTIC. No LLM can override it.
- An LLM can recommend, but this engine has final say on hard constraints.
- If evidence is missing, result is UNKNOWN, not ASSUMED.

Hard constraints evaluated:
1. Work authorization (citizenship/visa vs sponsorship_required)
2. Education requirements (degree level)
3. Minimum experience (years)
4. Location (if strictly on-site, check candidate willingness)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from app.domain.enums import WorkAuthorization


# ── Eligibility result types ──────────────────────────────────────────────────

class EligibilityStatus(str):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    UNKNOWN = "unknown"  # Missing evidence — cannot determine


@dataclass
class ConstraintResult:
    """Result of evaluating a single hard constraint."""

    constraint: str
    status: str  # EligibilityStatus value
    reason: str
    evidence: Optional[str] = None


@dataclass
class EligibilityResult:
    """Complete result of hard eligibility evaluation."""

    status: str  # EligibilityStatus value — overall verdict
    constraints: List[ConstraintResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status == EligibilityStatus.ELIGIBLE

    @property
    def failed_constraints(self) -> List[ConstraintResult]:
        return [c for c in self.constraints if c.status == EligibilityStatus.INELIGIBLE]

    @property
    def unknown_constraints(self) -> List[ConstraintResult]:
        return [c for c in self.constraints if c.status == EligibilityStatus.UNKNOWN]

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "passed": self.passed,
            "constraints": [
                {
                    "constraint": c.constraint,
                    "status": c.status,
                    "reason": c.reason,
                    "evidence": c.evidence,
                }
                for c in self.constraints
            ],
        }


# ── Education level hierarchy ─────────────────────────────────────────────────

EDUCATION_LEVELS = {
    "high_school": 1,
    "associate": 2,
    "bachelor": 3,
    "bachelors": 3,
    "b.s.": 3,
    "bs": 3,
    "b.e.": 3,
    "master": 4,
    "masters": 4,
    "m.s.": 4,
    "ms": 4,
    "mba": 4,
    "phd": 5,
    "ph.d": 5,
    "ph.d.": 5,
    "doctorate": 5,
}


def _get_education_level(degree: Optional[str]) -> int:
    """Convert a degree string to numeric level for comparison."""
    if not degree:
        return 0
    return EDUCATION_LEVELS.get(degree.lower().replace("'", "").strip(), 0)


# ── Individual constraint evaluators ─────────────────────────────────────────

def evaluate_work_authorization(
    candidate_authorization: Optional[str],
    job_sponsorship_required: Optional[bool],
    job_work_auth_required: Optional[bool],
) -> ConstraintResult:
    """
    Evaluate work authorization eligibility.

    Rules:
    - Citizens/PR: always pass (no sponsorship needed)
    - Work visa: pass unless job explicitly requires NO sponsorship
    - Requires sponsorship: fail if job requires work auth but no sponsorship
    - Not disclosed: UNKNOWN
    """
    constraint = "work_authorization"

    if candidate_authorization is None:
        return ConstraintResult(
            constraint=constraint,
            status=EligibilityStatus.UNKNOWN,
            reason="Candidate work authorization not disclosed",
        )

    # Job doesn't have explicit authorization requirements → pass
    if not job_work_auth_required and not job_sponsorship_required:
        return ConstraintResult(
            constraint=constraint,
            status=EligibilityStatus.ELIGIBLE,
            reason="Job has no explicit work authorization requirement",
            evidence=candidate_authorization,
        )

    auth = candidate_authorization.lower()

    if auth in (
        WorkAuthorization.CITIZEN.value,
        WorkAuthorization.PERMANENT_RESIDENT.value,
    ):
        return ConstraintResult(
            constraint=constraint,
            status=EligibilityStatus.ELIGIBLE,
            reason="Candidate is authorized to work without sponsorship",
            evidence=candidate_authorization,
        )

    if auth == WorkAuthorization.REQUIRES_SPONSORSHIP.value:
        if job_sponsorship_required is False:
            return ConstraintResult(
                constraint=constraint,
                status=EligibilityStatus.INELIGIBLE,
                reason="Job does not offer sponsorship and candidate requires it",
                evidence=candidate_authorization,
            )
        return ConstraintResult(
            constraint=constraint,
            status=EligibilityStatus.UNKNOWN,
            reason="Job sponsorship status unclear",
            evidence=candidate_authorization,
        )

    if auth == WorkAuthorization.WORK_VISA.value:
        return ConstraintResult(
            constraint=constraint,
            status=EligibilityStatus.ELIGIBLE,
            reason="Candidate has work visa authorization",
            evidence=candidate_authorization,
        )

    return ConstraintResult(
        constraint=constraint,
        status=EligibilityStatus.UNKNOWN,
        reason="Cannot determine work authorization eligibility",
    )


def evaluate_education(
    candidate_highest_degree: Optional[str],
    job_education_requirement: Optional[str],
) -> ConstraintResult:
    """
    Evaluate education eligibility.

    Only evaluates if job has an explicit education requirement.
    Returns UNKNOWN (not INELIGIBLE) if candidate degree is not provided.
    """
    constraint = "education"

    if not job_education_requirement:
        return ConstraintResult(
            constraint=constraint,
            status=EligibilityStatus.ELIGIBLE,
            reason="Job has no explicit education requirement",
        )

    if not candidate_highest_degree:
        return ConstraintResult(
            constraint=constraint,
            status=EligibilityStatus.UNKNOWN,
            reason="Candidate education not in profile",
        )

    required_level = _get_education_level(job_education_requirement)
    candidate_level = _get_education_level(candidate_highest_degree)

    if required_level == 0:
        return ConstraintResult(
            constraint=constraint,
            status=EligibilityStatus.UNKNOWN,
            reason=f"Could not parse education requirement: '{job_education_requirement}'",
        )

    if candidate_level >= required_level:
        return ConstraintResult(
            constraint=constraint,
            status=EligibilityStatus.ELIGIBLE,
            reason=f"Candidate degree meets or exceeds requirement",
            evidence=candidate_highest_degree,
        )

    return ConstraintResult(
        constraint=constraint,
        status=EligibilityStatus.INELIGIBLE,
        reason=f"Job requires {job_education_requirement}, candidate has {candidate_highest_degree}",
        evidence=candidate_highest_degree,
    )


def evaluate_experience(
    candidate_years: Optional[int],
    job_experience_requirement: Optional[str],
) -> ConstraintResult:
    """
    Evaluate minimum experience eligibility.

    Parses "X+ years" from job requirement string.
    """
    constraint = "experience"

    if not job_experience_requirement:
        return ConstraintResult(
            constraint=constraint,
            status=EligibilityStatus.ELIGIBLE,
            reason="Job has no explicit experience requirement",
        )

    import re
    exp_match = re.search(r"(\d+)", job_experience_requirement)
    if not exp_match:
        return ConstraintResult(
            constraint=constraint,
            status=EligibilityStatus.UNKNOWN,
            reason=f"Could not parse experience requirement: '{job_experience_requirement}'",
        )

    required_years = int(exp_match.group(1))

    if candidate_years is None:
        return ConstraintResult(
            constraint=constraint,
            status=EligibilityStatus.UNKNOWN,
            reason="Candidate years of experience not in profile",
        )

    if candidate_years >= required_years:
        return ConstraintResult(
            constraint=constraint,
            status=EligibilityStatus.ELIGIBLE,
            reason=f"Candidate has {candidate_years} years (required: {required_years}+)",
            evidence=str(candidate_years),
        )

    return ConstraintResult(
        constraint=constraint,
        status=EligibilityStatus.INELIGIBLE,
        reason=f"Job requires {required_years}+ years, candidate has {candidate_years}",
        evidence=str(candidate_years),
    )


def evaluate_location(
    candidate_willing_to_relocate: Optional[bool],
    candidate_country: Optional[str],
    job_remote_type: Optional[str],
    job_location: Optional[str],
) -> ConstraintResult:
    """
    Evaluate location eligibility.

    Remote and hybrid jobs: generally eligible.
    On-site jobs: eligible if willing to relocate or same country.
    """
    constraint = "location"

    if not job_remote_type or job_remote_type in ("remote", "unspecified"):
        return ConstraintResult(
            constraint=constraint,
            status=EligibilityStatus.ELIGIBLE,
            reason="Job is remote or remote type unspecified",
        )

    if job_remote_type == "hybrid":
        if candidate_willing_to_relocate:
            return ConstraintResult(
                constraint=constraint,
                status=EligibilityStatus.ELIGIBLE,
                reason="Candidate is willing to relocate for hybrid role",
            )
        return ConstraintResult(
            constraint=constraint,
            status=EligibilityStatus.UNKNOWN,
            reason="Hybrid role — commute feasibility unknown",
        )

    # Strictly on-site
    if candidate_willing_to_relocate:
        return ConstraintResult(
            constraint=constraint,
            status=EligibilityStatus.ELIGIBLE,
            reason="Candidate is willing to relocate",
            evidence=job_location,
        )

    if candidate_country and job_location:
        if candidate_country.lower() in job_location.lower():
            return ConstraintResult(
                constraint=constraint,
                status=EligibilityStatus.ELIGIBLE,
                reason="Job location matches candidate country",
            )

    return ConstraintResult(
        constraint=constraint,
        status=EligibilityStatus.UNKNOWN,
        reason="On-site role — candidate relocation preference unknown",
    )


# ── Main eligibility evaluator ────────────────────────────────────────────────

def evaluate_hard_eligibility(
    *,
    # Candidate data
    candidate_work_authorization: Optional[str],
    candidate_highest_degree: Optional[str],
    candidate_years_of_experience: Optional[int],
    candidate_willing_to_relocate: Optional[bool],
    candidate_country: Optional[str],
    # Job requirements
    job_sponsorship_required: Optional[bool],
    job_work_auth_required: Optional[bool],
    job_education_requirement: Optional[str],
    job_experience_requirement: Optional[str],
    job_remote_type: Optional[str],
    job_location: Optional[str],
) -> EligibilityResult:
    """
    Run all hard eligibility checks.

    Returns EligibilityResult with overall verdict and per-constraint details.

    Rules:
    - Any INELIGIBLE constraint → overall INELIGIBLE
    - No INELIGIBLE but has UNKNOWN → overall UNKNOWN
    - All ELIGIBLE → overall ELIGIBLE
    """
    constraints = [
        evaluate_work_authorization(
            candidate_work_authorization,
            job_sponsorship_required,
            job_work_auth_required,
        ),
        evaluate_education(candidate_highest_degree, job_education_requirement),
        evaluate_experience(candidate_years_of_experience, job_experience_requirement),
        evaluate_location(
            candidate_willing_to_relocate,
            candidate_country,
            job_remote_type,
            job_location,
        ),
    ]

    # Aggregate verdict
    statuses = {c.status for c in constraints}

    if EligibilityStatus.INELIGIBLE in statuses:
        overall = EligibilityStatus.INELIGIBLE
    elif EligibilityStatus.UNKNOWN in statuses:
        overall = EligibilityStatus.UNKNOWN
    else:
        overall = EligibilityStatus.ELIGIBLE

    return EligibilityResult(status=overall, constraints=constraints)
