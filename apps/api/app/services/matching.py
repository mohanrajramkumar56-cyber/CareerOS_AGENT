"""
CareerOS - Matching Engine (Phase 3).

Evaluates how well a candidate matches a job.
Combines hard eligibility (deterministic) with skill scoring.

Architecture:
- Hard eligibility via eligibility.py (MUST pass — no LLM override)
- Skill match score: Jaccard similarity between candidate skills and job requirements
- Gap analysis: skill_gap vs representation_gap classification
- Result persisted as JobMatch record
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.evidence import can_claim_be_used, classify_gap
from app.domain.enums import EvidenceStrength, GapType
from app.models.job import Job, JobMatch
from app.models.candidate_profile import CandidateProfile
from app.models.candidate import Skill, Education, Experience
from app.services.eligibility import (
    EligibilityStatus,
    evaluate_hard_eligibility,
)


# ── Skill scoring ─────────────────────────────────────────────────────────────

def _parse_skills(raw: Optional[str]) -> List[str]:
    """Parse comma-separated skill string into normalised list."""
    if not raw:
        return []
    return [s.strip().lower() for s in raw.split(",") if s.strip()]


def compute_skill_match_score(
    candidate_skills: List[str],
    mandatory_skills: List[str],
    preferred_skills: List[str],
) -> float:
    """
    Compute a weighted skill match score (0.0 → 1.0).

    Mandatory skills are weighted 2x vs preferred skills.
    Returns 1.0 if no skills are required.
    """
    if not mandatory_skills and not preferred_skills:
        return 1.0

    candidate_set = set(s.lower() for s in candidate_skills)

    mandatory_matched = sum(1 for s in mandatory_skills if s.lower() in candidate_set)
    preferred_matched = sum(1 for s in preferred_skills if s.lower() in candidate_set)

    # Weighted score: mandatory weight = 2, preferred weight = 1
    total_weight = len(mandatory_skills) * 2 + len(preferred_skills)
    if total_weight == 0:
        return 1.0

    matched_weight = mandatory_matched * 2 + preferred_matched
    return round(matched_weight / total_weight, 4)


def analyse_skill_gaps(
    candidate_skills: List[str],
    candidate_facts: List[Dict[str, Any]],
    required_skills: List[str],
) -> Tuple[List[str], List[str]]:
    """
    Classify each required skill as skill_gap or representation_gap.

    - skill_gap: candidate has no evidence for this skill
    - representation_gap: candidate has evidence but it's not in their resume/facts
      i.e. the skill exists in candidate_skills but not in verified facts

    Returns (skill_gaps, representation_gaps).
    """
    candidate_skill_set = set(s.lower() for s in candidate_skills)

    # Facts that are usable (UNKNOWN facts don't count)
    usable_fact_skills = set()
    for fact in candidate_facts:
        strength = fact.get("evidence_strength", "unknown")
        if can_claim_be_used(strength):
            claim = fact.get("claim", "").lower()
            usable_fact_skills.add(claim)

    skill_gaps: List[str] = []
    representation_gaps: List[str] = []

    for skill in required_skills:
        skill_lower = skill.lower()
        if skill_lower in candidate_skill_set:
            # Has the skill — is it well-represented?
            represented = any(skill_lower in uf for uf in usable_fact_skills)
            if not represented:
                representation_gaps.append(skill)
            # Else: fine — not a gap
        else:
            skill_gaps.append(skill)

    return skill_gaps, representation_gaps


# ── Main match evaluator ──────────────────────────────────────────────────────

async def compute_match(
    db: AsyncSession,
    job: Job,
    candidate: CandidateProfile,
) -> JobMatch:
    """
    Compute a full match between a job and a candidate.

    Steps:
    1. Hard eligibility evaluation (deterministic)
    2. Skill match score
    3. Gap analysis
    4. Persist or update JobMatch record

    Returns the persisted JobMatch.
    """
    # ── 1. Fetch candidate sub-resources ──────────────────────────────────────
    skills_result = await db.execute(
        select(Skill).where(
            and_(Skill.candidate_id == candidate.id, Skill.deleted_at.is_(None))
        )
    )
    skills = list(skills_result.scalars().all())
    candidate_skill_names = [s.name for s in skills]

    # Get education for highest degree
    edu_result = await db.execute(
        select(Education).where(
            and_(Education.candidate_id == candidate.id, Education.deleted_at.is_(None))
        )
    )
    educations = list(edu_result.scalars().all())
    # Simple heuristic: pick the most recent non-null degree
    highest_degree: Optional[str] = None
    for edu in educations:
        if edu.degree:
            highest_degree = edu.degree
            break

    # ── 2. Hard eligibility ───────────────────────────────────────────────────
    eligibility = evaluate_hard_eligibility(
        candidate_work_authorization=candidate.work_authorization,
        candidate_highest_degree=highest_degree,
        candidate_years_of_experience=candidate.years_of_experience,
        candidate_willing_to_relocate=candidate.willing_to_relocate,
        candidate_country=candidate.current_country,
        job_sponsorship_required=job.sponsorship_required,
        job_work_auth_required=job.work_authorization_required,
        job_education_requirement=job.education_requirements,
        job_experience_requirement=job.experience_requirements,
        job_remote_type=job.remote_type,
        job_location=job.location,
    )

    # ── 3. Skill scoring ──────────────────────────────────────────────────────
    mandatory_skills = _parse_skills(job.mandatory_skills)
    preferred_skills = _parse_skills(job.preferred_skills)
    all_required = mandatory_skills + preferred_skills

    skill_score = compute_skill_match_score(
        candidate_skill_names, mandatory_skills, preferred_skills
    )

    # ── 4. Gap analysis ───────────────────────────────────────────────────────
    skill_gaps, representation_gaps = analyse_skill_gaps(
        candidate_skill_names,
        [],  # facts loaded lazily — simplified for Phase 3
        all_required,
    )

    # ── 5. Requirements matched/missing ──────────────────────────────────────
    candidate_skill_set = set(s.lower() for s in candidate_skill_names)
    matched_reqs = [s for s in all_required if s.lower() in candidate_skill_set]
    missing_reqs = [s for s in all_required if s.lower() not in candidate_skill_set]

    # ── 6. Confidence score ───────────────────────────────────────────────────
    # Simple composite: 60% skill match + 40% eligibility bonus
    eligibility_bonus = (
        1.0 if eligibility.status == EligibilityStatus.ELIGIBLE
        else 0.5 if eligibility.status == EligibilityStatus.UNKNOWN
        else 0.0
    )
    confidence = round(0.6 * skill_score + 0.4 * eligibility_bonus, 4)

    # ── 7. Build explanation ──────────────────────────────────────────────────
    failed = [c.reason for c in eligibility.failed_constraints]
    unknown = [c.constraint for c in eligibility.unknown_constraints]
    explanation_parts = []
    if eligibility.status == EligibilityStatus.ELIGIBLE:
        explanation_parts.append("Passes all hard eligibility constraints.")
    elif eligibility.status == EligibilityStatus.INELIGIBLE:
        explanation_parts.append(f"Fails hard constraints: {'; '.join(failed)}.")
    else:
        explanation_parts.append(f"Eligibility unclear ({', '.join(unknown)}).")
    explanation_parts.append(
        f"Skill match: {round(skill_score * 100)}% "
        f"({len(matched_reqs)}/{len(all_required)} required skills matched)."
    )
    if skill_gaps:
        explanation_parts.append(f"Missing skills: {', '.join(skill_gaps[:5])}.")
    if representation_gaps:
        explanation_parts.append(f"Under-represented: {', '.join(representation_gaps[:5])}.")
    explanation = " ".join(explanation_parts)

    # ── 8. Persist or update JobMatch ─────────────────────────────────────────
    existing_result = await db.execute(
        select(JobMatch).where(
            and_(
                JobMatch.job_id == job.id,
                JobMatch.candidate_id == candidate.id,
            )
        )
    )
    existing = existing_result.scalar_one_or_none()

    hard_constraints_failed_str = (
        ",".join(c.constraint for c in eligibility.failed_constraints)
        if eligibility.failed_constraints
        else None
    )

    if existing:
        # Update existing match
        existing.eligible = eligibility.status
        existing.hard_constraints_passed = eligibility.status != EligibilityStatus.INELIGIBLE
        existing.hard_constraints_failed = hard_constraints_failed_str
        existing.skill_match_score = skill_score
        existing.matched_requirements = json.dumps(matched_reqs)
        existing.missing_requirements = json.dumps(missing_reqs)
        existing.skill_gaps = json.dumps(skill_gaps)
        existing.representation_gaps = json.dumps(representation_gaps)
        existing.confidence = confidence
        existing.explanation = explanation
        await db.flush()
        await db.refresh(existing)
        return existing

    match = JobMatch(
        job_id=job.id,
        candidate_id=candidate.id,
        eligible=eligibility.status,
        hard_constraints_passed=eligibility.status != EligibilityStatus.INELIGIBLE,
        hard_constraints_failed=hard_constraints_failed_str,
        skill_match_score=skill_score,
        semantic_similarity=None,  # pgvector — Phase 9
        matched_requirements=json.dumps(matched_reqs),
        missing_requirements=json.dumps(missing_reqs),
        skill_gaps=json.dumps(skill_gaps),
        representation_gaps=json.dumps(representation_gaps),
        confidence=confidence,
        explanation=explanation,
    )
    db.add(match)
    await db.flush()
    await db.refresh(match)
    return match


async def get_matches_for_candidate(
    db: AsyncSession,
    candidate_id: uuid.UUID,
    eligible_only: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[JobMatch], int]:
    """Return paginated JobMatch records for a candidate, with jobs eager-loaded."""
    from sqlalchemy.orm import joinedload
    from sqlalchemy import func

    conditions = [JobMatch.candidate_id == candidate_id]
    if eligible_only:
        conditions.append(JobMatch.eligible == EligibilityStatus.ELIGIBLE)

    count_result = await db.execute(
        select(func.count()).select_from(JobMatch).where(and_(*conditions))
    )
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        select(JobMatch)
        .options(joinedload(JobMatch.job))
        .where(and_(*conditions))
        .order_by(JobMatch.confidence.desc().nulls_last())
        .offset(offset)
        .limit(page_size)
    )
    matches = list(result.scalars().unique().all())
    return matches, total


async def get_match(
    db: AsyncSession,
    job_id: uuid.UUID,
    candidate_id: uuid.UUID,
) -> Optional[JobMatch]:
    """Fetch a specific match by job + candidate."""
    result = await db.execute(
        select(JobMatch).where(
            and_(
                JobMatch.job_id == job_id,
                JobMatch.candidate_id == candidate_id,
            )
        )
    )
    return result.scalar_one_or_none()
