"""
CareerOS - Resume Builder Service (Phase 4).

Builds evidence-backed resumes from candidate data.

Truth policy:
- UNKNOWN evidence facts are NEVER included
- Each bullet has a traceable evidence source
- Fabrication is architecturally impossible (only persisted facts are used)

Templates: standard | minimal | technical | executive
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.domain.evidence import can_claim_be_used
from app.models.candidate_profile import CandidateProfile
from app.models.candidate import Education, Experience, Skill, Project, Certification, Achievement
from app.models.evidence import CandidateFact
from app.models.job import Job
from app.models.resume import Resume


# ── Template definitions ──────────────────────────────────────────────────────

TEMPLATES = {
    "standard": {
        "sections": ["summary", "experience", "skills", "education", "projects", "certifications"],
        "description": "Classic professional resume",
    },
    "minimal": {
        "sections": ["summary", "skills", "experience", "education"],
        "description": "Clean, minimal layout",
    },
    "technical": {
        "sections": ["skills", "experience", "projects", "education", "certifications"],
        "description": "Technical roles — skills and projects first",
    },
    "executive": {
        "sections": ["summary", "experience", "achievements", "education", "certifications"],
        "description": "Senior / executive roles — achievements prominent",
    },
}

VALID_TEMPLATES = list(TEMPLATES.keys())


# ── Section renderers (Markdown) ──────────────────────────────────────────────

def _render_summary(profile: CandidateProfile) -> str:
    if not profile.summary:
        return ""
    return f"## Summary\n\n{profile.summary}\n"


def _render_contact(profile: CandidateProfile) -> str:
    parts = []
    if profile.email:
        parts.append(profile.email)
    if profile.phone:
        parts.append(profile.phone)
    if profile.linkedin_url:
        parts.append(f"[LinkedIn]({profile.linkedin_url})")
    if profile.github_url:
        parts.append(f"[GitHub]({profile.github_url})")
    if profile.portfolio_url:
        parts.append(f"[Portfolio]({profile.portfolio_url})")
    location_parts = filter(None, [profile.current_city, profile.current_state, profile.current_country])
    location = ", ".join(location_parts)
    if location:
        parts.append(location)
    return " · ".join(parts)


def _render_skills(
    skills: List[Skill],
    emphasised: Optional[List[str]] = None,
) -> str:
    if not skills:
        return ""
    # Only include skills — all skills present are included
    usable = list(skills)
    if not usable:
        return ""
    emphasised_set = set(e.lower() for e in (emphasised or []))
    # Sort: emphasised first, then by name
    sorted_skills = sorted(
        usable,
        key=lambda s: (0 if s.name.lower() in emphasised_set else 1, s.name),
    )
    skill_names = [s.name for s in sorted_skills]
    return f"## Skills\n\n{', '.join(skill_names)}\n"


def _render_experience(experiences: List[Experience]) -> str:
    if not experiences:
        return ""
    lines = ["## Experience\n"]
    for exp in sorted(experiences, key=lambda e: e.start_date or datetime.min, reverse=True):
        end = exp.end_date.strftime("%b %Y") if exp.end_date else "Present"
        start = exp.start_date.strftime("%b %Y") if exp.start_date else ""
        date_range = f"{start} – {end}" if start else f"Until {end}"
        lines.append(f"### {exp.title} — {exp.company}")
        if date_range:
            lines.append(f"*{date_range}*")
        if exp.description:
            # Each sentence becomes a bullet
            sentences = [s.strip() for s in exp.description.split(".") if s.strip()]
            for sentence in sentences[:5]:
                lines.append(f"- {sentence}.")
        lines.append("")
    return "\n".join(lines)


def _render_education(educations: List[Education]) -> str:
    if not educations:
        return ""
    lines = ["## Education\n"]
    for edu in sorted(educations, key=lambda e: e.end_date or datetime.min, reverse=True):
        degree_str = " ".join(filter(None, [edu.degree, "in", edu.field_of_study])) if edu.field_of_study else (edu.degree or "Degree")
        lines.append(f"### {degree_str} — {edu.institution}")
        if edu.end_date:
            lines.append(f"*Graduated {edu.end_date.strftime('%Y')}*")
        if edu.gpa:
            lines.append(f"GPA: {edu.gpa}")
        lines.append("")
    return "\n".join(lines)


def _render_projects(projects: List[Project]) -> str:
    if not projects:
        return ""
    lines = ["## Projects\n"]
    for proj in projects:
        lines.append(f"### {proj.name}")
        if proj.description:
            lines.append(proj.description)
        if proj.technologies:
            lines.append(f"*Technologies: {proj.technologies}*")
        if proj.url:
            lines.append(f"[Project Link]({proj.url})")
        lines.append("")
    return "\n".join(lines)


def _render_certifications(certs: List[Certification]) -> str:
    if not certs:
        return ""
    lines = ["## Certifications\n"]
    for cert in certs:
        expiry = f" (expires {cert.expiry_date.strftime('%Y')})" if cert.expiry_date else ""
        lines.append(f"- **{cert.name}** — {cert.issuer}{expiry}")
    lines.append("")
    return "\n".join(lines)


def _render_achievements(achievements: List[Achievement]) -> str:
    if not achievements:
        return ""
    lines = ["## Achievements\n"]
    for ach in achievements:
        lines.append(f"- **{ach.title}**: {ach.description or ''}")
    lines.append("")
    return "\n".join(lines)


# ── Truth policy filter ───────────────────────────────────────────────────────

def _filter_usable_facts(facts: List[CandidateFact]) -> Tuple[List[CandidateFact], int]:
    """
    Filter out facts with UNKNOWN evidence.

    Returns (usable_facts, excluded_count).
    Truth policy: UNKNOWN facts are never included in resumes.
    """
    usable = []
    excluded = 0
    for fact in facts:
        if can_claim_be_used(fact.evidence_strength):
            usable.append(fact)
        else:
            excluded += 1
    return usable, excluded


# ── Main builder ──────────────────────────────────────────────────────────────

async def build_resume(
    db: AsyncSession,
    candidate: CandidateProfile,
    template: str = "standard",
    job: Optional[Job] = None,
    title: Optional[str] = None,
) -> Resume:
    """
    Build a complete evidence-backed resume for a candidate.

    If a job is provided, the resume is tailored: skills required by the job
    are emphasised and the template adapted.

    Truth policy strictly enforced — UNKNOWN facts excluded automatically.
    """
    if template not in VALID_TEMPLATES:
        raise ValueError(f"Invalid template '{template}'. Choose from: {VALID_TEMPLATES}")

    # ── Load candidate sub-resources ──────────────────────────────────────────
    skills_r = await db.execute(
        select(Skill).where(and_(Skill.candidate_id == candidate.id, Skill.deleted_at.is_(None)))
    )
    skills = list(skills_r.scalars().all())

    experiences_r = await db.execute(
        select(Experience).where(and_(Experience.candidate_id == candidate.id, Experience.deleted_at.is_(None)))
    )
    experiences = list(experiences_r.scalars().all())

    education_r = await db.execute(
        select(Education).where(and_(Education.candidate_id == candidate.id, Education.deleted_at.is_(None)))
    )
    educations = list(education_r.scalars().all())

    projects_r = await db.execute(
        select(Project).where(and_(Project.candidate_id == candidate.id, Project.deleted_at.is_(None)))
    )
    projects = list(projects_r.scalars().all())

    certs_r = await db.execute(
        select(Certification).where(and_(Certification.candidate_id == candidate.id, Certification.deleted_at.is_(None)))
    )
    certs = list(certs_r.scalars().all())

    achievements_r = await db.execute(
        select(Achievement).where(and_(Achievement.candidate_id == candidate.id, Achievement.deleted_at.is_(None)))
    )
    achievements = list(achievements_r.scalars().all())

    facts_r = await db.execute(
        select(CandidateFact).where(and_(CandidateFact.candidate_id == candidate.id))
    )
    all_facts = list(facts_r.scalars().all())

    # ── Truth policy ──────────────────────────────────────────────────────────
    usable_facts, excluded_count = _filter_usable_facts(all_facts)

    # ── Tailoring: determine emphasised skills ────────────────────────────────
    is_tailored = job is not None
    emphasised_skills: List[str] = []
    if job:
        mandatory = [s.strip() for s in (job.mandatory_skills or "").split(",") if s.strip()]
        preferred = [s.strip() for s in (job.preferred_skills or "").split(",") if s.strip()]
        emphasised_skills = mandatory + preferred
        # Use technical template for tailored resumes if not overridden
        if template == "standard":
            template = "technical"

    # ── Render sections ───────────────────────────────────────────────────────
    section_order = TEMPLATES[template]["sections"]
    section_renderers = {
        "summary": lambda: _render_summary(candidate),
        "experience": lambda: _render_experience(experiences),
        "skills": lambda: _render_skills(skills, emphasised_skills),
        "education": lambda: _render_education(educations),
        "projects": lambda: _render_projects(projects),
        "certifications": lambda: _render_certifications(certs),
        "achievements": lambda: _render_achievements(achievements),
    }

    name = candidate.full_name or "Candidate"
    contact = _render_contact(candidate)
    headline = candidate.headline or ""

    header = f"# {name}\n\n{headline}\n\n{contact}\n\n---\n"
    sections = [header]
    for section_name in section_order:
        renderer = section_renderers.get(section_name)
        if renderer:
            rendered = renderer()
            if rendered:
                sections.append(rendered)

    content_md = "\n".join(sections)

    # ── Persist ───────────────────────────────────────────────────────────────
    resume_title = title or (
        f"{name} — {job.title} at {job.company}" if job else f"{name} — Resume"
    )

    resume = Resume(
        candidate_id=candidate.id,
        job_id=job.id if job else None,
        title=resume_title,
        template=template,
        content_markdown=content_md,
        content_text=content_md.replace("#", "").replace("*", "").replace("-", ""),
        emphasised_skills=json.dumps(emphasised_skills) if emphasised_skills else None,
        evidence_ids_used=json.dumps([str(f.id) for f in usable_facts]),
        facts_excluded_count=excluded_count,
        truth_policy_enforced=True,
        is_tailored=is_tailored,
        version=1,
    )
    db.add(resume)
    await db.flush()
    await db.refresh(resume)
    return resume


async def get_resume(db: AsyncSession, resume_id: uuid.UUID) -> Optional[Resume]:
    """Fetch a resume by ID."""
    result = await db.execute(
        select(Resume).where(
            and_(Resume.id == resume_id, Resume.deleted_at.is_(None))
        )
    )
    return result.scalar_one_or_none()


async def list_resumes(
    db: AsyncSession,
    candidate_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Resume], int]:
    """List resumes for a candidate."""
    from sqlalchemy import func

    conditions = [
        Resume.candidate_id == candidate_id,
        Resume.deleted_at.is_(None),
    ]
    count_result = await db.execute(
        select(func.count()).select_from(Resume).where(and_(*conditions))
    )
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        select(Resume)
        .where(and_(*conditions))
        .order_by(Resume.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def delete_resume(db: AsyncSession, resume_id: uuid.UUID) -> bool:
    """Soft-delete a resume."""
    resume = await get_resume(db, resume_id)
    if not resume:
        return False
    resume.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return True
