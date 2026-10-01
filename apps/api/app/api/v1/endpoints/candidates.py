"""
CareerOS - Candidate API endpoints.

All endpoints are scoped to the authenticated user's candidate profile.
Authorization: a user can only access their own candidate data.

Routes:
  POST   /candidates/profile          - create profile
  GET    /candidates/profile          - get own profile (summary)
  PUT    /candidates/profile          - update own profile
  GET    /candidates/profile/full     - get full profile with all sub-resources

  POST   /candidates/education        - add education
  GET    /candidates/education        - list education
  PUT    /candidates/education/{id}   - update education
  DELETE /candidates/education/{id}   - delete education

  POST   /candidates/experiences      - add experience
  GET    /candidates/experiences      - list experiences
  PUT    /candidates/experiences/{id} - update experience
  DELETE /candidates/experiences/{id} - delete experience

  POST   /candidates/skills           - add skill
  GET    /candidates/skills           - list skills
  DELETE /candidates/skills/{id}      - delete skill

  POST   /candidates/projects         - add project
  GET    /candidates/projects         - list projects
  PUT    /candidates/projects/{id}    - update project
  DELETE /candidates/projects/{id}    - delete project

  POST   /candidates/certifications   - add certification
  GET    /candidates/certifications   - list certifications
  DELETE /candidates/certifications/{id} - delete certification

  POST   /candidates/achievements     - add achievement
  GET    /candidates/achievements     - list achievements
  DELETE /candidates/achievements/{id} - delete achievement

  POST   /candidates/facts            - create a candidate fact with evidence
  GET    /candidates/facts            - list facts (optional ?category=skill)
  GET    /candidates/facts/{id}       - get fact with evidence
  POST   /candidates/facts/{id}/evidence - add evidence to a fact
"""
from __future__ import annotations

import uuid
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.candidate import (
    AchievementCreate,
    AchievementResponse,
    CandidateFactCreate,
    CandidateFactResponse,
    CandidateProfileCreate,
    CandidateProfileFull,
    CandidateProfileResponse,
    CandidateProfileUpdate,
    CertificationCreate,
    CertificationResponse,
    EducationCreate,
    EducationResponse,
    EducationUpdate,
    EvidenceCreate,
    EvidenceResponse,
    ExperienceCreate,
    ExperienceResponse,
    ExperienceUpdate,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    SkillCreate,
    SkillResponse,
    SkillUpdate,
    CertificationUpdate,
    AchievementUpdate,
)
from app.services import candidate as svc

router = APIRouter()


# ── Profile ───────────────────────────────────────────────────────────────────

@router.post("/profile", response_model=CandidateProfileResponse, status_code=201)
async def create_profile(
    payload: CandidateProfileCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CandidateProfileResponse:
    """Create the candidate profile for the authenticated user."""
    try:
        profile = await svc.create_profile(db, current_user.id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return CandidateProfileResponse.model_validate(profile)


@router.get("/profile", response_model=CandidateProfileResponse)
async def get_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CandidateProfileResponse:
    """Get the authenticated user's candidate profile."""
    profile = await svc.get_profile_by_user(db, current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
    return CandidateProfileResponse.model_validate(profile)


@router.put("/profile", response_model=CandidateProfileResponse)
async def update_profile(
    payload: CandidateProfileUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CandidateProfileResponse:
    """Update the authenticated user's candidate profile."""
    profile = await svc.get_profile_by_user(db, current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
    updated = await svc.update_profile(db, profile, payload)
    return CandidateProfileResponse.model_validate(updated)


@router.get("/profile/full", response_model=CandidateProfileFull)
async def get_full_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CandidateProfileFull:
    """Get the full candidate profile with all sub-resources."""
    profile = await svc.get_profile_by_user(db, current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
    full = await svc.get_profile_full(db, profile.id)
    if not full:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
    return CandidateProfileFull.model_validate(full)


# ── Education ─────────────────────────────────────────────────────────────────

async def _require_profile(
    db: AsyncSession, user_id: uuid.UUID
) -> uuid.UUID:
    """Helper: require a profile to exist and return its ID."""
    profile = await svc.get_profile_by_user(db, user_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Candidate profile not found. Create one first.",
        )
    return profile.id


@router.post("/education", response_model=EducationResponse, status_code=201)
async def create_education(
    payload: EducationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EducationResponse:
    candidate_id = await _require_profile(db, current_user.id)
    edu = await svc.create_education(db, candidate_id, payload)
    return EducationResponse.model_validate(edu)


@router.get("/education", response_model=List[EducationResponse])
async def list_education(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> List[EducationResponse]:
    candidate_id = await _require_profile(db, current_user.id)
    items = await svc.list_education(db, candidate_id)
    return [EducationResponse.model_validate(e) for e in items]


@router.put("/education/{education_id}", response_model=EducationResponse)
async def update_education(
    education_id: uuid.UUID,
    payload: EducationUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EducationResponse:
    candidate_id = await _require_profile(db, current_user.id)
    edu = await svc.get_education(db, education_id, candidate_id)
    if not edu:
        raise HTTPException(status_code=404, detail="Education entry not found")
    updated = await svc.update_education(db, edu, payload)
    return EducationResponse.model_validate(updated)


@router.delete("/education/{education_id}", status_code=204)
async def delete_education(
    education_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    candidate_id = await _require_profile(db, current_user.id)
    edu = await svc.get_education(db, education_id, candidate_id)
    if not edu:
        raise HTTPException(status_code=404, detail="Education entry not found")
    await svc.delete_education(db, edu)
    return Response(status_code=204)


# ── Experience ────────────────────────────────────────────────────────────────

@router.post("/experiences", response_model=ExperienceResponse, status_code=201)
async def create_experience(
    payload: ExperienceCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExperienceResponse:
    candidate_id = await _require_profile(db, current_user.id)
    exp = await svc.create_experience(db, candidate_id, payload)
    return ExperienceResponse.model_validate(exp)


@router.get("/experiences", response_model=List[ExperienceResponse])
async def list_experiences(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> List[ExperienceResponse]:
    candidate_id = await _require_profile(db, current_user.id)
    items = await svc.list_experiences(db, candidate_id)
    return [ExperienceResponse.model_validate(e) for e in items]


@router.put("/experiences/{experience_id}", response_model=ExperienceResponse)
async def update_experience(
    experience_id: uuid.UUID,
    payload: ExperienceUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExperienceResponse:
    candidate_id = await _require_profile(db, current_user.id)
    exp = await svc.get_experience(db, experience_id, candidate_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experience entry not found")
    updated = await svc.update_experience(db, exp, payload)
    return ExperienceResponse.model_validate(updated)


@router.delete("/experiences/{experience_id}", status_code=204)
async def delete_experience(
    experience_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    candidate_id = await _require_profile(db, current_user.id)
    exp = await svc.get_experience(db, experience_id, candidate_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experience entry not found")
    await svc.delete_experience(db, exp)
    return Response(status_code=204)


# ── Skills ────────────────────────────────────────────────────────────────────

@router.post("/skills", response_model=SkillResponse, status_code=201)
async def create_skill(
    payload: SkillCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SkillResponse:
    candidate_id = await _require_profile(db, current_user.id)
    try:
        skill = await svc.create_skill(db, candidate_id, payload)
    except Exception as e:
        if "uq_candidate_skill_name" in str(e).lower() or "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail=f"Skill '{payload.name}' already exists")
        raise
    return SkillResponse.model_validate(skill)


@router.get("/skills", response_model=List[SkillResponse])
async def list_skills(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> List[SkillResponse]:
    candidate_id = await _require_profile(db, current_user.id)
    items = await svc.list_skills(db, candidate_id)
    return [SkillResponse.model_validate(s) for s in items]


@router.delete("/skills/{skill_id}", status_code=204)
async def delete_skill(
    skill_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    candidate_id = await _require_profile(db, current_user.id)
    skill = await svc.get_skill(db, skill_id, candidate_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    await svc.delete_skill(db, skill)
    return Response(status_code=204)


# ── Projects ──────────────────────────────────────────────────────────────────

@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(
    payload: ProjectCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectResponse:
    candidate_id = await _require_profile(db, current_user.id)
    project = await svc.create_project(db, candidate_id, payload)
    return ProjectResponse.model_validate(project)


@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> List[ProjectResponse]:
    candidate_id = await _require_profile(db, current_user.id)
    items = await svc.list_projects(db, candidate_id)
    return [ProjectResponse.model_validate(p) for p in items]


@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectResponse:
    candidate_id = await _require_profile(db, current_user.id)
    project = await svc.get_project(db, project_id, candidate_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    from sqlalchemy.ext.asyncio import AsyncSession as _AS
    await db.flush()
    await db.refresh(project)
    return ProjectResponse.model_validate(project)


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(
    project_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    candidate_id = await _require_profile(db, current_user.id)
    project = await svc.get_project(db, project_id, candidate_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await svc.delete_project(db, project)
    return Response(status_code=204)


# ── Certifications ────────────────────────────────────────────────────────────

@router.post("/certifications", response_model=CertificationResponse, status_code=201)
async def create_certification(
    payload: CertificationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CertificationResponse:
    candidate_id = await _require_profile(db, current_user.id)
    cert = await svc.create_certification(db, candidate_id, payload)
    return CertificationResponse.model_validate(cert)


@router.get("/certifications", response_model=List[CertificationResponse])
async def list_certifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> List[CertificationResponse]:
    candidate_id = await _require_profile(db, current_user.id)
    items = await svc.list_certifications(db, candidate_id)
    return [CertificationResponse.model_validate(c) for c in items]


@router.delete("/certifications/{cert_id}", status_code=204)
async def delete_certification(
    cert_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    candidate_id = await _require_profile(db, current_user.id)
    cert = await svc.get_certification(db, cert_id, candidate_id)
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")
    await svc.delete_certification(db, cert)
    return Response(status_code=204)


# ── Achievements ──────────────────────────────────────────────────────────────

@router.post("/achievements", response_model=AchievementResponse, status_code=201)
async def create_achievement(
    payload: AchievementCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AchievementResponse:
    candidate_id = await _require_profile(db, current_user.id)
    ach = await svc.create_achievement(db, candidate_id, payload)
    return AchievementResponse.model_validate(ach)


@router.get("/achievements", response_model=List[AchievementResponse])
async def list_achievements(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> List[AchievementResponse]:
    candidate_id = await _require_profile(db, current_user.id)
    items = await svc.list_achievements(db, candidate_id)
    return [AchievementResponse.model_validate(a) for a in items]


@router.delete("/achievements/{ach_id}", status_code=204)
async def delete_achievement(
    ach_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    candidate_id = await _require_profile(db, current_user.id)
    ach = await svc.get_achievement(db, ach_id, candidate_id)
    if not ach:
        raise HTTPException(status_code=404, detail="Achievement not found")
    await svc.delete_achievement(db, ach)
    return Response(status_code=204)


# ── Evidence / Facts ──────────────────────────────────────────────────────────

@router.post("/facts", response_model=CandidateFactResponse, status_code=201)
async def create_fact(
    payload: CandidateFactCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CandidateFactResponse:
    """Create a candidate fact with optional evidence entries."""
    candidate_id = await _require_profile(db, current_user.id)
    fact = await svc.create_fact(db, candidate_id, payload)
    # Reload with evidence
    loaded = await svc.get_fact(db, fact.id, candidate_id)
    return CandidateFactResponse.model_validate(loaded)


@router.get("/facts", response_model=List[CandidateFactResponse])
async def list_facts(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    category: Optional[str] = Query(default=None, description="Filter by FactCategory"),
) -> List[CandidateFactResponse]:
    candidate_id = await _require_profile(db, current_user.id)
    facts = await svc.list_facts(db, candidate_id, category=category)
    return [CandidateFactResponse.model_validate(f) for f in facts]


@router.get("/facts/{fact_id}", response_model=CandidateFactResponse)
async def get_fact(
    fact_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CandidateFactResponse:
    candidate_id = await _require_profile(db, current_user.id)
    fact = await svc.get_fact(db, fact_id, candidate_id)
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")
    return CandidateFactResponse.model_validate(fact)


@router.post("/facts/{fact_id}/evidence", response_model=EvidenceResponse, status_code=201)
async def add_evidence(
    fact_id: uuid.UUID,
    payload: EvidenceCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EvidenceResponse:
    """Add evidence to an existing candidate fact."""
    candidate_id = await _require_profile(db, current_user.id)
    fact = await svc.get_fact(db, fact_id, candidate_id)
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")
    evidence = await svc.add_evidence_to_fact(db, fact, payload)
    return EvidenceResponse.model_validate(evidence)
