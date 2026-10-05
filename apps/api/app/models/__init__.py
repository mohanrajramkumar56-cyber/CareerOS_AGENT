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
from app.models.job import Job, JobMatch
from app.models.resume import Resume
from app.models.application import Application
from app.models.browser_session import BrowserSession
from app.models.policy import PolicyRule, AuditLog
from app.models.email_message import EmailMessage

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
    # Jobs
    "Job",
    "JobMatch",
    # Resume
    "Resume",
    # Application
    "Application",
    # Browser automation
    "BrowserSession",
    # Policy + Security
    "PolicyRule",
    "AuditLog",
    # Email
    "EmailMessage",
]
