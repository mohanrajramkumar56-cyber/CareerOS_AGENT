"""
CareerOS - Job Intelligence Pipeline.

Pipeline stages:
1. Normalization  - standardize fields across sources
2. Deduplication  - prevent storing duplicate jobs
3. Freshness      - track and update job validity
4. Extraction     - parse skills, education, experience from job text

All functions are deterministic — no LLMs involved in this pipeline.
LLM-assisted extraction is added in Phase 3 (matching) as an enhancement.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import EmploymentType, RemoteType
from app.models.job import Job


# ── Normalization ─────────────────────────────────────────────────────────────

REMOTE_KEYWORDS = {
    "remote", "fully remote", "work from home", "wfh", "distributed", "anywhere"
}
HYBRID_KEYWORDS = {"hybrid", "part remote", "flexible", "in-office part-time"}
ONSITE_KEYWORDS = {"on-site", "onsite", "in-office", "in office", "on site"}

FULL_TIME_KEYWORDS = {"full-time", "full time", "ft", "permanent"}
PART_TIME_KEYWORDS = {"part-time", "part time", "pt"}
CONTRACT_KEYWORDS = {"contract", "contractor", "c2c", "c2h", "contract to hire"}
INTERNSHIP_KEYWORDS = {"intern", "internship", "co-op", "coop"}
FREELANCE_KEYWORDS = {"freelance", "freelancer", "independent"}

SALARY_PATTERN = re.compile(
    r"\$\s*([\d,]+(?:\.\d+)?)\s*(?:k)?\s*[-–—]\s*\$?\s*([\d,]+(?:\.\d+)?)\s*(?:k)?",
    re.IGNORECASE,
)

SALARY_SINGLE_PATTERN = re.compile(
    r"\$\s*([\d,]+(?:\.\d+)?)\s*(?:k)?\s*(?:/yr|/year|/hour|/hr|a year)?",
    re.IGNORECASE,
)


def normalize_remote_type(text: str) -> str:
    """Infer remote type from job text. Returns RemoteType enum value."""
    if not text:
        return RemoteType.UNSPECIFIED.value
    low = text.lower()
    if any(kw in low for kw in HYBRID_KEYWORDS):
        return RemoteType.HYBRID.value
    if any(kw in low for kw in REMOTE_KEYWORDS):
        return RemoteType.REMOTE.value
    if any(kw in low for kw in ONSITE_KEYWORDS):
        return RemoteType.ONSITE.value
    return RemoteType.UNSPECIFIED.value


def normalize_employment_type(text: str) -> str:
    """Infer employment type from job text. Returns EmploymentType enum value."""
    if not text:
        return EmploymentType.UNSPECIFIED.value
    low = text.lower()
    if any(kw in low for kw in INTERNSHIP_KEYWORDS):
        return EmploymentType.INTERNSHIP.value
    if any(kw in low for kw in CONTRACT_KEYWORDS):
        return EmploymentType.CONTRACT.value
    if any(kw in low for kw in FREELANCE_KEYWORDS):
        return EmploymentType.FREELANCE.value
    if any(kw in low for kw in PART_TIME_KEYWORDS):
        return EmploymentType.PART_TIME.value
    if any(kw in low for kw in FULL_TIME_KEYWORDS):
        return EmploymentType.FULL_TIME.value
    return EmploymentType.UNSPECIFIED.value


def extract_salary_from_text(text: str) -> Tuple[Optional[int], Optional[int], str]:
    """
    Extract salary range from job description text.

    Returns (min_salary, max_salary, currency).
    """
    if not text:
        return None, None, "USD"

    match = SALARY_PATTERN.search(text)
    if match:
        raw_min = match.group(1).replace(",", "")
        raw_max = match.group(2).replace(",", "")
        min_val = float(raw_min)
        max_val = float(raw_max)
        # Handle "k" suffix
        if "k" in text[match.start() : match.end()].lower():
            min_val *= 1000
            max_val *= 1000
        return int(min_val), int(max_val), "USD"

    match = SALARY_SINGLE_PATTERN.search(text)
    if match:
        raw = match.group(1).replace(",", "")
        val = float(raw)
        if "k" in text[match.start() : match.end()].lower():
            val *= 1000
        return int(val), int(val), "USD"

    return None, None, "USD"


def compute_content_hash(company: str, title: str, location: Optional[str]) -> str:
    """
    Compute a stable content hash for deduplication.

    Hash is based on normalized company, title, location.
    """
    canonical = f"{company.strip().lower()}|{title.strip().lower()}|{(location or '').strip().lower()}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ── Deduplication ─────────────────────────────────────────────────────────────

async def find_duplicate(
    db: AsyncSession,
    source: str,
    source_job_id: Optional[str],
    source_url: Optional[str],
    content_hash: str,
) -> Optional[Job]:
    """
    Check if a job already exists using multiple deduplication signals.

    Priority:
    1. Same source + source_job_id (exact match from same source)
    2. Same canonical URL
    3. Same content hash (same job, possibly from different source)
    """
    # Signal 1: source ID match
    if source_job_id:
        result = await db.execute(
            select(Job).where(
                and_(
                    Job.source == source,
                    Job.source_job_id == source_job_id,
                    Job.deleted_at.is_(None),
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

    # Signal 2: URL match
    if source_url:
        result = await db.execute(
            select(Job).where(
                and_(
                    Job.source_url == source_url,
                    Job.deleted_at.is_(None),
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

    # Signal 3: content hash match
    result = await db.execute(
        select(Job).where(
            and_(
                Job.content_hash == content_hash,
                Job.deleted_at.is_(None),
            )
        )
    )
    return result.scalar_one_or_none()


# ── Freshness ─────────────────────────────────────────────────────────────────

STALE_THRESHOLD_DAYS = 30   # After 30 days without verification, mark stale
EXPIRED_THRESHOLD_DAYS = 90  # After 90 days, mark expired


def compute_freshness_status(
    posted_at: Optional[datetime],
    discovered_at: Optional[datetime],
    last_verified_at: Optional[datetime],
    expires_at: Optional[datetime],
) -> str:
    """
    Compute freshness status deterministically.

    Returns one of: new, active, stale, expired, unknown
    """
    now = datetime.now(timezone.utc)

    # If explicitly expired
    if expires_at:
        expires_aware = expires_at if expires_at.tzinfo is not None else expires_at.replace(tzinfo=timezone.utc)
        if now > expires_aware:
            return "expired"

    # Reference time: last verification if available, else discovered_at
    reference = last_verified_at or discovered_at
    if reference is None:
        return "unknown"

    # Ensure timezone awareness
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)

    age_days = (now - reference).days

    if age_days > EXPIRED_THRESHOLD_DAYS:
        return "expired"
    if age_days > STALE_THRESHOLD_DAYS:
        return "stale"

    # If discovered in last 3 days with no prior existence, call it "new"
    if discovered_at:
        disc_aware = discovered_at if discovered_at.tzinfo else discovered_at.replace(tzinfo=timezone.utc)
        if (now - disc_aware).days <= 3:
            return "new"

    return "active"


async def update_stale_jobs(db: AsyncSession) -> int:
    """
    Update freshness status for all jobs that have gone stale.
    Returns count of updated jobs.
    """
    now = datetime.now(timezone.utc)
    stale_threshold = now - timedelta(days=STALE_THRESHOLD_DAYS)
    expired_threshold = now - timedelta(days=EXPIRED_THRESHOLD_DAYS)

    result = await db.execute(
        select(Job).where(
            and_(
                Job.deleted_at.is_(None),
                Job.freshness_status.in_(["new", "active"]),
            )
        )
    )
    jobs = result.scalars().all()

    updated = 0
    for job in jobs:
        new_status = compute_freshness_status(
            posted_at=job.posted_at,
            discovered_at=job.discovered_at,
            last_verified_at=job.last_verified_at,
            expires_at=job.expires_at,
        )
        if new_status != job.freshness_status:
            job.freshness_status = new_status
            updated += 1

    if updated > 0:
        await db.flush()

    return updated


# ── Requirement extraction ────────────────────────────────────────────────────

# Known technology and skill keywords for rule-based extraction
PROGRAMMING_LANGUAGES = {
    "python", "java", "javascript", "typescript", "go", "rust", "c++", "c#",
    "ruby", "php", "scala", "kotlin", "swift", "r", "matlab", "perl",
}

FRAMEWORKS = {
    "react", "angular", "vue", "next.js", "fastapi", "django", "flask",
    "spring", "node.js", "express", "rails", "laravel", "nestjs",
}

DATABASES = {
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "cassandra",
    "sqlite", "oracle", "dynamodb", "bigquery", "snowflake",
}

CLOUD_PLATFORMS = {
    "aws", "gcp", "azure", "kubernetes", "docker", "terraform",
    "helm", "jenkins", "gitlab", "github actions",
}

EXPERIENCE_PATTERN = re.compile(
    r"(\d+)\+?\s*(?:to\s*\d+)?\s*years?\s*(?:of\s*)?(?:experience|exp)",
    re.IGNORECASE,
)

EDUCATION_DEGREE_PATTERN = re.compile(
    r"\b(bachelor(?:'?s)?|master(?:'?s)?|phd|ph\.?d|mba|b\.?s\.?|m\.?s\.?|b\.?e\.?)\b",
    re.IGNORECASE,
)


def extract_skills_from_text(text: str) -> Tuple[List[str], List[str]]:
    """
    Extract mandatory and preferred skills from job description.

    Returns (mandatory_skills, preferred_skills).
    Uses rule-based extraction — deterministic, no LLM.
    """
    if not text:
        return [], []

    low = text.lower()
    found_skills: Set[str] = set()

    for skill_set in (PROGRAMMING_LANGUAGES, FRAMEWORKS, DATABASES, CLOUD_PLATFORMS):
        for skill in skill_set:
            # Whole-word matching
            pattern = r"\b" + re.escape(skill) + r"\b"
            if re.search(pattern, low):
                found_skills.add(skill)

    # Heuristic: skills in "required" sections → mandatory
    # Skills in "nice to have" or "preferred" sections → preferred
    mandatory: List[str] = []
    preferred: List[str] = []

    required_section = _find_section(
        text, ["required", "requirements", "must have", "you will need"]
    )
    preferred_section = _find_section(
        text, ["preferred", "nice to have", "bonus", "plus", "desired"]
    )

    for skill in found_skills:
        skill_pattern = r"\b" + re.escape(skill) + r"\b"
        in_required = bool(required_section and re.search(skill_pattern, required_section, re.IGNORECASE))
        in_preferred = bool(preferred_section and re.search(skill_pattern, preferred_section, re.IGNORECASE))

        if in_preferred and not in_required:
            preferred.append(skill)
        else:
            mandatory.append(skill)  # Default to mandatory if unclear

    return sorted(mandatory), sorted(preferred)


def extract_experience_requirements(text: str) -> Optional[str]:
    """Extract minimum years of experience requirement."""
    if not text:
        return None
    matches = EXPERIENCE_PATTERN.findall(text)
    if matches:
        years = sorted([int(m) for m in matches])
        return f"{years[0]}+ years"
    return None


def extract_education_requirements(text: str) -> Optional[str]:
    """Extract minimum education requirement."""
    if not text:
        return None
    matches = EDUCATION_DEGREE_PATTERN.findall(text)
    if not matches:
        return None

    # Normalize to highest found
    degree_priority = {
        "phd": 5, "ph.d": 5, "ph.d.": 5,
        "mba": 4, "masters": 4, "master's": 4, "m.s.": 4, "ms": 4,
        "bachelors": 3, "bachelor's": 3, "b.s.": 3, "bs": 3, "b.e.": 3,
    }
    max_level = 0
    result = None
    for match in matches:
        level = degree_priority.get(match.lower().replace("'", ""), 1)
        if level > max_level:
            max_level = level
            result = match

    return result


def _find_section(text: str, section_keywords: List[str]) -> Optional[str]:
    """Find a specific section of the job description by keywords."""
    for keyword in section_keywords:
        pattern = re.compile(
            r"(?:^|\n)(?:[#*-]?\s*)" + re.escape(keyword) + r"\s*:?\s*\n([\s\S]{20,800}?)(?:\n\n|\Z)",
            re.IGNORECASE,
        )
        match = pattern.search(text)
        if match:
            return match.group(1)
    return None


def extract_all_requirements(description: str) -> Dict[str, any]:
    """
    Run all extraction rules on a job description.

    Returns a dict ready to update the Job model.
    """
    if not description:
        return {
            "mandatory_skills": None,
            "preferred_skills": None,
            "experience_requirements": None,
            "education_requirements": None,
            "work_authorization_required": None,
            "sponsorship_required": None,
        }
    mandatory_skills, preferred_skills = extract_skills_from_text(description)
    experience_req = extract_experience_requirements(description)
    education_req = extract_education_requirements(description)

    # Detect authorization keywords
    auth_text = description.lower()
    work_auth_required = any(
        kw in auth_text
        for kw in ["authorized to work", "work authorization", "us citizen", "security clearance"]
    )
    sponsorship = any(
        kw in auth_text
        for kw in ["sponsorship", "sponsor", "visa sponsor", "h1b"]
    )

    return {
        "mandatory_skills": ",".join(mandatory_skills) if mandatory_skills else None,
        "preferred_skills": ",".join(preferred_skills) if preferred_skills else None,
        "experience_requirements": experience_req,
        "education_requirements": education_req,
        "work_authorization_required": work_auth_required or None,
        "sponsorship_required": sponsorship or None,
    }


# ── Job ingestion pipeline ────────────────────────────────────────────────────

async def ingest_job(
    db: AsyncSession,
    job_data: Dict,
) -> Tuple[Job, bool]:
    """
    Run the full job ingestion pipeline:
    1. Normalize fields
    2. Check deduplication
    3. Extract requirements
    4. Set freshness status
    5. Persist or return existing

    Returns (job, was_created).
    """
    # Normalize remote type from description + location
    combined_text = " ".join(filter(None, [
        job_data.get("description", ""),
        job_data.get("location", ""),
        job_data.get("title", ""),
    ]))

    remote_type = normalize_remote_type(combined_text)
    employment_type = normalize_employment_type(combined_text)

    # Extract salary if not provided
    salary_min = job_data.get("salary_min")
    salary_max = job_data.get("salary_max")
    if not salary_min and not salary_max:
        salary_min, salary_max, _ = extract_salary_from_text(combined_text)

    # Compute deduplication hash
    content_hash = compute_content_hash(
        company=job_data.get("company", ""),
        title=job_data.get("title", ""),
        location=job_data.get("location"),
    )

    # Check deduplication
    existing = await find_duplicate(
        db,
        source=job_data.get("source", ""),
        source_job_id=job_data.get("source_job_id"),
        source_url=job_data.get("source_url"),
        content_hash=content_hash,
    )
    if existing:
        # Update last_verified_at for freshness tracking
        existing.last_verified_at = datetime.now(timezone.utc)
        existing.freshness_status = compute_freshness_status(
            posted_at=existing.posted_at,
            discovered_at=existing.discovered_at,
            last_verified_at=existing.last_verified_at,
            expires_at=existing.expires_at,
        )
        await db.flush()
        await db.refresh(existing)
        return existing, False

    # Extract requirements from description
    description = job_data.get("description", "")
    extracted = extract_all_requirements(description)

    # Caller-provided skill/requirement fields take priority over auto-extracted ones
    for field in ("mandatory_skills", "preferred_skills", "education_requirements",
                  "experience_requirements", "work_authorization_required", "sponsorship_required",
                  "certifications"):
        if job_data.get(field) is not None:
            extracted[field] = job_data[field]

    # Set freshness status
    posted_at = job_data.get("posted_at")
    if isinstance(posted_at, str):
        try:
            from dateutil.parser import parse
            posted_at = parse(posted_at)
        except Exception:
            posted_at = None

    now = datetime.now(timezone.utc)
    freshness_status = compute_freshness_status(
        posted_at=posted_at,
        discovered_at=now,
        last_verified_at=None,
        expires_at=job_data.get("expires_at"),
    )

    # Create new job
    job = Job(
        source=job_data.get("source", "unknown"),
        source_job_id=job_data.get("source_job_id"),
        source_url=job_data.get("source_url"),
        company=job_data.get("company", "Unknown"),
        title=job_data.get("title", "Unknown"),
        location=job_data.get("location"),
        remote_type=remote_type,
        employment_type=employment_type,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=job_data.get("salary_currency", "USD"),
        description=description,
        responsibilities=job_data.get("responsibilities"),
        requirements=job_data.get("requirements"),
        application_url=job_data.get("application_url"),
        posted_at=posted_at,
        discovered_at=now,
        freshness_status=freshness_status,
        content_hash=content_hash,
        normalized_at=now,
        normalized=True,
        **extracted,
    )

    db.add(job)
    await db.flush()
    await db.refresh(job)
    return job, True
