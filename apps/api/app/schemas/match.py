"""
CareerOS - Matching Engine Pydantic schemas (Phase 3).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.job import JobResponse


class MatchRequest(BaseModel):
    """Request to compute a match for a specific job."""
    job_id: uuid.UUID


class MatchResponse(BaseModel):
    """Full match result between a candidate and a job."""
    id: uuid.UUID
    job_id: uuid.UUID
    candidate_id: uuid.UUID
    eligible: str
    hard_constraints_passed: bool
    hard_constraints_failed: Optional[str]
    skill_match_score: Optional[float]
    semantic_similarity: Optional[float]
    matched_requirements: Optional[str]  # JSON array string
    missing_requirements: Optional[str]  # JSON array string
    skill_gaps: Optional[str]            # JSON array string
    representation_gaps: Optional[str]   # JSON array string
    confidence: Optional[float]
    explanation: Optional[str]
    created_at: datetime
    updated_at: datetime
    job: Optional[JobResponse] = None

    model_config = {"from_attributes": True}


class MatchListResponse(BaseModel):
    """Paginated list of matches."""
    matches: List[MatchResponse]
    total: int
    page: int
    page_size: int
