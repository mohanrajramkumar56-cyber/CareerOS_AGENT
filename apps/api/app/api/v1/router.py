"""
CareerOS API v1 - Router aggregator.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    candidates,
    jobs,
    health,
    matches,
    resumes,
    applications,
    dashboard,
    policies,
    audit,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(candidates.router, prefix="/candidates", tags=["candidates"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(matches.router, prefix="/matches", tags=["matches"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(policies.router, prefix="/policies", tags=["policies"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(health.router, prefix="/system", tags=["system"])
