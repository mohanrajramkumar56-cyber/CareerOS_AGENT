"""
CareerOS - ORM models registry.
Import all models here so Alembic auto-detects them.
"""
from app.models.user import User, UserSession
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

__all__ = [
    # Auth
    "User",
    "UserSession",
    # Candidate
    "CandidateProfile",
    "Education",
    "Experience",
    "Skill",
    "Project",
    "Certification",
    "Achievement",
    # Evidence graph
    "CandidateFact",
    "Evidence",
]
