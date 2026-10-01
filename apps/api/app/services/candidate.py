"""
CareerOS - Candidate service layer.

All candidate CRUD operations plus evidence validation enforcement.
Services own the business logic; endpoints own HTTP concerns only.

Truth policy is enforced here:
- Facts with UNKNOWN strength are persisted but flagged
- Evidence validation runs on every fact/evidence upsert
- Aggregate strength is recomputed whenever evidence changes
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import List, Optional, Sequence

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.evidence import validate_evidence, _compute_strength
from app.domain.enums import EvidenceStrength, EvidenceSourceType, FactCategory
from app.models.candidate_profile import CandidateProfile
from app.models.candidate import (
    Education,
    Experience,
    Skill,
    Project,
    Certification,
    Achievement,
)
from app.models.evidence import CandidateFact, Evidence
from app.schemas.candidate import (
    CandidateProfileCreate,
    CandidateProfileUpdate,
    EducationCreate,
    EducationUpdate,
    ExperienceCreate,
    ExperienceUpdate,
    SkillCreate,
    SkillUpdate,
    ProjectCreate,
    ProjectUpdate,
    CertificationCreate,
    CertificationUpdate,
    AchievementCreate,
    AchievementUpdate,
    CandidateFactCreate,
    EvidenceCreate,
)


# ── Profile ───────────────────────────────────────────────────────────────────

async def get_profile_by_user(
    db: AsyncSession, user_id: uuid.UUID
) -> Optional[CandidateProfile]:
    """Get a candidate profile owned by a user."""
    result = await db.execute(
        select(CandidateProfile).where(
            and_(
                CandidateProfile.user_id == user_id,
                CandidateProfile.deleted_at.is_(None),
            )
        )
    )
    return result.scalar_one_or_none()


async def get_profile_full(
    db: AsyncSession, profile_id: uuid.UUID
) -> Optional[CandidateProfile]:
    """Get a profile with all nested relationships eagerly loaded."""
    result = await db.execute(
        select(CandidateProfile)
        .options(
            selectinload(CandidateProfile.education),
            selectinload(CandidateProfile.experiences),
            selectinload(CandidateProfile.skills),
            selectinload(CandidateProfile.projects),
            selectinload(CandidateProfile.certifications),
            selectinload(CandidateProfile.achievements),
            selectinload(CandidateProfile.facts).selectinload(
                CandidateFact.evidence_entries
            ),
        )
        .where(
            and_(
                CandidateProfile.id == profile_id,
                CandidateProfile.deleted_at.is_(None),
            )
        )
    )
    return result.scalar_one_or_none()


async def create_profile(
    db: AsyncSession,
    user_id: uuid.UUID,
    data: CandidateProfileCreate,
) -> CandidateProfile:
    """Create a candidate profile for a user. Raises ValueError if one already exists."""
    existing = await get_profile_by_user(db, user_id)
    if existing:
        raise ValueError("Candidate profile already exists for this user")

    profile = CandidateProfile(
        user_id=user_id,
        **data.model_dump(exclude_none=True),
    )
    # Normalize enum values to strings for storage
    if data.preferred_remote_type:
        profile.preferred_remote_type = data.preferred_remote_type.value
    if data.preferred_employment_type:
        profile.preferred_employment_type = data.preferred_employment_type.value
    if data.work_authorization:
        profile.work_authorization = data.work_authorization.value

    db.add(profile)
    await db.flush()
    await db.refresh(profile)
    return profile


async def update_profile(
    db: AsyncSession,
    profile: CandidateProfile,
    data: CandidateProfileUpdate,
) -> CandidateProfile:
    """Partial update of a candidate profile."""
    update_data = data.model_dump(exclude_unset=True)

    # Normalize enums
    for enum_field in ("preferred_remote_type", "preferred_employment_type", "work_authorization"):
        if enum_field in update_data and update_data[enum_field] is not None:
            update_data[enum_field] = update_data[enum_field].value

    for field, value in update_data.items():
        setattr(profile, field, value)

    await db.flush()
    await db.refresh(profile)
    return profile


# ── Education ─────────────────────────────────────────────────────────────────

async def list_education(
    db: AsyncSession, candidate_id: uuid.UUID
) -> Sequence[Education]:
    result = await db.execute(
        select(Education).where(
            and_(
                Education.candidate_id == candidate_id,
                Education.deleted_at.is_(None),
            )
        )
    )
    return result.scalars().all()


async def create_education(
    db: AsyncSession, candidate_id: uuid.UUID, data: EducationCreate
) -> Education:
    edu = Education(candidate_id=candidate_id, **data.model_dump(exclude_none=True))
    db.add(edu)
    await db.flush()
    await db.refresh(edu)
    return edu


async def get_education(
    db: AsyncSession, education_id: uuid.UUID, candidate_id: uuid.UUID
) -> Optional[Education]:
    result = await db.execute(
        select(Education).where(
            and_(
                Education.id == education_id,
                Education.candidate_id == candidate_id,
                Education.deleted_at.is_(None),
            )
        )
    )
    return result.scalar_one_or_none()


async def update_education(
    db: AsyncSession, edu: Education, data: EducationUpdate
) -> Education:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(edu, field, value)
    await db.flush()
    await db.refresh(edu)
    return edu


async def delete_education(db: AsyncSession, edu: Education) -> None:
    from datetime import datetime, timezone
    edu.deleted_at = datetime.now(timezone.utc)
    await db.flush()


# ── Experience ────────────────────────────────────────────────────────────────

async def list_experiences(
    db: AsyncSession, candidate_id: uuid.UUID
) -> Sequence[Experience]:
    result = await db.execute(
        select(Experience).where(
            and_(
                Experience.candidate_id == candidate_id,
                Experience.deleted_at.is_(None),
            )
        )
    )
    return result.scalars().all()


async def create_experience(
    db: AsyncSession, candidate_id: uuid.UUID, data: ExperienceCreate
) -> Experience:
    exp_data = data.model_dump(exclude_none=True)
    if data.employment_type:
        exp_data["employment_type"] = data.employment_type.value

    # Compute duration_months if both dates provided
    if data.start_date and data.end_date:
        delta = data.end_date - data.start_date
        exp_data["duration_months"] = max(0, delta.days // 30)
    elif data.start_date and data.is_current:
        delta = date.today() - data.start_date
        exp_data["duration_months"] = max(0, delta.days // 30)

    exp = Experience(candidate_id=candidate_id, **exp_data)
    db.add(exp)
    await db.flush()
    await db.refresh(exp)
    return exp


async def get_experience(
    db: AsyncSession, exp_id: uuid.UUID, candidate_id: uuid.UUID
) -> Optional[Experience]:
    result = await db.execute(
        select(Experience).where(
            and_(
                Experience.id == exp_id,
                Experience.candidate_id == candidate_id,
                Experience.deleted_at.is_(None),
            )
        )
    )
    return result.scalar_one_or_none()


async def update_experience(
    db: AsyncSession, exp: Experience, data: ExperienceUpdate
) -> Experience:
    update_data = data.model_dump(exclude_unset=True)
    if "employment_type" in update_data and update_data["employment_type"]:
        update_data["employment_type"] = update_data["employment_type"].value
    for field, value in update_data.items():
        setattr(exp, field, value)
    await db.flush()
    await db.refresh(exp)
    return exp


async def delete_experience(db: AsyncSession, exp: Experience) -> None:
    from datetime import datetime, timezone
    exp.deleted_at = datetime.now(timezone.utc)
    await db.flush()


# ── Skills ────────────────────────────────────────────────────────────────────

async def list_skills(
    db: AsyncSession, candidate_id: uuid.UUID
) -> Sequence[Skill]:
    result = await db.execute(
        select(Skill).where(
            and_(
                Skill.candidate_id == candidate_id,
                Skill.deleted_at.is_(None),
            )
        )
    )
    return result.scalars().all()


async def create_skill(
    db: AsyncSession, candidate_id: uuid.UUID, data: SkillCreate
) -> Skill:
    skill = Skill(candidate_id=candidate_id, **data.model_dump(exclude_none=True))
    db.add(skill)
    await db.flush()
    await db.refresh(skill)
    return skill


async def get_skill(
    db: AsyncSession, skill_id: uuid.UUID, candidate_id: uuid.UUID
) -> Optional[Skill]:
    result = await db.execute(
        select(Skill).where(
            and_(
                Skill.id == skill_id,
                Skill.candidate_id == candidate_id,
                Skill.deleted_at.is_(None),
            )
        )
    )
    return result.scalar_one_or_none()


async def delete_skill(db: AsyncSession, skill: Skill) -> None:
    from datetime import datetime, timezone
    skill.deleted_at = datetime.now(timezone.utc)
    await db.flush()


# ── Projects ──────────────────────────────────────────────────────────────────

async def list_projects(
    db: AsyncSession, candidate_id: uuid.UUID
) -> Sequence[Project]:
    result = await db.execute(
        select(Project).where(
            and_(
                Project.candidate_id == candidate_id,
                Project.deleted_at.is_(None),
            )
        )
    )
    return result.scalars().all()


async def create_project(
    db: AsyncSession, candidate_id: uuid.UUID, data: ProjectCreate
) -> Project:
    project = Project(candidate_id=candidate_id, **data.model_dump(exclude_none=True))
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


async def get_project(
    db: AsyncSession, project_id: uuid.UUID, candidate_id: uuid.UUID
) -> Optional[Project]:
    result = await db.execute(
        select(Project).where(
            and_(
                Project.id == project_id,
                Project.candidate_id == candidate_id,
                Project.deleted_at.is_(None),
            )
        )
    )
    return result.scalar_one_or_none()


async def delete_project(db: AsyncSession, project: Project) -> None:
    from datetime import datetime, timezone
    project.deleted_at = datetime.now(timezone.utc)
    await db.flush()


# ── Certifications ────────────────────────────────────────────────────────────

async def list_certifications(
    db: AsyncSession, candidate_id: uuid.UUID
) -> Sequence[Certification]:
    result = await db.execute(
        select(Certification).where(
            and_(
                Certification.candidate_id == candidate_id,
                Certification.deleted_at.is_(None),
            )
        )
    )
    return result.scalars().all()


async def create_certification(
    db: AsyncSession, candidate_id: uuid.UUID, data: CertificationCreate
) -> Certification:
    cert = Certification(
        candidate_id=candidate_id, **data.model_dump(exclude_none=True)
    )
    db.add(cert)
    await db.flush()
    await db.refresh(cert)
    return cert


async def get_certification(
    db: AsyncSession, cert_id: uuid.UUID, candidate_id: uuid.UUID
) -> Optional[Certification]:
    result = await db.execute(
        select(Certification).where(
            and_(
                Certification.id == cert_id,
                Certification.candidate_id == candidate_id,
                Certification.deleted_at.is_(None),
            )
        )
    )
    return result.scalar_one_or_none()


async def delete_certification(db: AsyncSession, cert: Certification) -> None:
    from datetime import datetime, timezone
    cert.deleted_at = datetime.now(timezone.utc)
    await db.flush()


# ── Achievements ──────────────────────────────────────────────────────────────

async def list_achievements(
    db: AsyncSession, candidate_id: uuid.UUID
) -> Sequence[Achievement]:
    result = await db.execute(
        select(Achievement).where(
            and_(
                Achievement.candidate_id == candidate_id,
                Achievement.deleted_at.is_(None),
            )
        )
    )
    return result.scalars().all()


async def create_achievement(
    db: AsyncSession, candidate_id: uuid.UUID, data: AchievementCreate
) -> Achievement:
    ach = Achievement(
        candidate_id=candidate_id, **data.model_dump(exclude_none=True)
    )
    db.add(ach)
    await db.flush()
    await db.refresh(ach)
    return ach


async def get_achievement(
    db: AsyncSession, ach_id: uuid.UUID, candidate_id: uuid.UUID
) -> Optional[Achievement]:
    result = await db.execute(
        select(Achievement).where(
            and_(
                Achievement.id == ach_id,
                Achievement.candidate_id == candidate_id,
                Achievement.deleted_at.is_(None),
            )
        )
    )
    return result.scalar_one_or_none()


async def delete_achievement(db: AsyncSession, ach: Achievement) -> None:
    from datetime import datetime, timezone
    ach.deleted_at = datetime.now(timezone.utc)
    await db.flush()


# ── Evidence graph ────────────────────────────────────────────────────────────

async def list_facts(
    db: AsyncSession,
    candidate_id: uuid.UUID,
    category: Optional[str] = None,
) -> Sequence[CandidateFact]:
    filters = [CandidateFact.candidate_id == candidate_id]
    if category:
        filters.append(CandidateFact.category == category)
    result = await db.execute(
        select(CandidateFact)
        .options(selectinload(CandidateFact.evidence_entries))
        .where(and_(*filters))
    )
    return result.scalars().all()


async def create_fact(
    db: AsyncSession,
    candidate_id: uuid.UUID,
    data: CandidateFactCreate,
) -> CandidateFact:
    """
    Create a CandidateFact and link its evidence entries.
    Runs evidence validation and computes aggregate strength.
    """
    # Create the fact
    fact = CandidateFact(
        candidate_id=candidate_id,
        category=data.category.value,
        claim=data.claim,
        normalized_value=data.normalized_value,
        evidence_strength=EvidenceStrength.UNKNOWN.value,
    )
    db.add(fact)
    await db.flush()

    # Attach evidence entries and compute aggregate strength
    if data.evidence:
        strengths = []
        for ev_data in data.evidence:
            source_type_enum = ev_data.source_type
            validation = validate_evidence(
                claim=data.claim,
                category=data.category,
                source_type=source_type_enum,
                source_reference=ev_data.source_reference,
                normalized_value=data.normalized_value,
            )
            ev = Evidence(
                fact_id=fact.id,
                source_type=source_type_enum.value,
                source_reference=ev_data.source_reference,
                description=ev_data.description,
                strength=validation.strength.value,
            )
            db.add(ev)
            strengths.append(validation.strength)

        # Aggregate: use the strongest evidence entry
        aggregate = _aggregate_strength(strengths)
        fact.evidence_strength = aggregate.value

    await db.flush()
    await db.refresh(fact)
    return fact


async def get_fact(
    db: AsyncSession, fact_id: uuid.UUID, candidate_id: uuid.UUID
) -> Optional[CandidateFact]:
    result = await db.execute(
        select(CandidateFact)
        .options(selectinload(CandidateFact.evidence_entries))
        .where(
            and_(
                CandidateFact.id == fact_id,
                CandidateFact.candidate_id == candidate_id,
            )
        )
    )
    return result.scalar_one_or_none()


async def add_evidence_to_fact(
    db: AsyncSession,
    fact: CandidateFact,
    data: EvidenceCreate,
) -> Evidence:
    """
    Add a new evidence entry to an existing fact.
    Recomputes the fact's aggregate strength.
    """
    validation = validate_evidence(
        claim=fact.claim,
        category=FactCategory(fact.category),
        source_type=data.source_type,
        source_reference=data.source_reference,
        normalized_value=fact.normalized_value,
    )

    ev = Evidence(
        fact_id=fact.id,
        source_type=data.source_type.value,
        source_reference=data.source_reference,
        description=data.description,
        strength=validation.strength.value,
    )
    db.add(ev)
    await db.flush()

    # Reload all evidence entries and recompute aggregate
    await _recompute_fact_strength(db, fact)
    await db.refresh(ev)
    return ev


async def _recompute_fact_strength(
    db: AsyncSession, fact: CandidateFact
) -> None:
    """Recompute and persist the aggregate evidence strength for a fact."""
    result = await db.execute(
        select(Evidence).where(Evidence.fact_id == fact.id)
    )
    all_evidence = result.scalars().all()
    strengths = [EvidenceStrength(ev.strength) for ev in all_evidence]
    aggregate = _aggregate_strength(strengths)
    fact.evidence_strength = aggregate.value
    await db.flush()


def _aggregate_strength(strengths: List[EvidenceStrength]) -> EvidenceStrength:
    """
    Compute aggregate strength from multiple evidence entries.
    Uses the strongest single piece of evidence.
    """
    if not strengths:
        return EvidenceStrength.UNKNOWN

    priority = [
        EvidenceStrength.VERIFIED,
        EvidenceStrength.STRONG,
        EvidenceStrength.MODERATE,
        EvidenceStrength.WEAK,
        EvidenceStrength.UNKNOWN,
    ]
    for level in priority:
        if level in strengths:
            return level
    return EvidenceStrength.UNKNOWN
