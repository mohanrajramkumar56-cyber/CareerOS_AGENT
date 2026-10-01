"""
CareerOS API v1 - Router aggregator.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, candidates, jobs, health

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(candidates.router, prefix="/candidates", tags=["candidates"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(health.router, prefix="/system", tags=["system"])
