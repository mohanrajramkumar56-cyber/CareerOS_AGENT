"""
CareerOS - Policy rules API endpoints (Phase 8).

Routes:
  POST   /policies/          - create a policy rule for current candidate
  GET    /policies/          - list all policy rules for current candidate
  GET    /policies/actions   - list all valid action names
  GET    /policies/{id}      - get single policy rule
  PUT    /policies/{id}      - update policy rule
  DELETE /policies/{id}      - delete policy rule
"""
from __future__ import annotations

import uuid
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.policy import PolicyRule
from app.models.user import User
from app.schemas.policy import PolicyRuleCreate, PolicyRuleResponse, PolicyRuleUpdate
from app.services.candidate import get_profile_by_user

router = APIRouter()

VALID_ACTIONS: List[str] = [
    "job.discover",
    "job.match",
    "resume.generate",
    "application.prepare",
    "application.submit",
    "email.send_followup",
    "notification.send",
    "browser.fill_form",
]


async def _get_candidate_or_404(db: AsyncSession, user: User):
    profile = await get_profile_by_user(db, user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found",
        )
    return profile


async def _get_policy_for_candidate(
    db: AsyncSession, policy_id: uuid.UUID, candidate_id: uuid.UUID
) -> PolicyRule:
    result = await db.execute(
        select(PolicyRule).where(
            PolicyRule.id == policy_id,
            PolicyRule.candidate_id == candidate_id,
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy rule not found",
        )
    return rule


# ── GET /policies/actions ─────────────────────────────────────────────────────
# Must be defined before /{id} to avoid route shadowing

@router.get("/actions", response_model=List[str])
async def list_valid_actions(
    current_user: Annotated[User, Depends(get_current_user)],
) -> List[str]:
    """Return all valid action names that can be used in policy rules."""
    return VALID_ACTIONS


# ── POST /policies/ ──────────────────────────────────────────────────────────

@router.post("/", response_model=PolicyRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_policy_rule(
    payload: PolicyRuleCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PolicyRuleResponse:
    """Create a policy rule for the current user's candidate."""
    if payload.action not in VALID_ACTIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid action '{payload.action}'. Valid actions: {VALID_ACTIONS}",
        )

    candidate = await _get_candidate_or_404(db, current_user)

    rule = PolicyRule(
        candidate_id=candidate.id,
        action=payload.action,
        enabled=payload.enabled,
        requires_approval=payload.requires_approval,
        max_per_day=payload.max_per_day,
        max_per_week=payload.max_per_week,
        conditions=payload.conditions,
        description=payload.description,
    )
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return PolicyRuleResponse.model_validate(rule)


# ── GET /policies/ ────────────────────────────────────────────────────────────

@router.get("/", response_model=List[PolicyRuleResponse])
async def list_policy_rules(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> List[PolicyRuleResponse]:
    """List all policy rules for the current candidate."""
    candidate = await _get_candidate_or_404(db, current_user)
    result = await db.execute(
        select(PolicyRule).where(PolicyRule.candidate_id == candidate.id)
    )
    rules = result.scalars().all()
    return [PolicyRuleResponse.model_validate(r) for r in rules]


# ── GET /policies/{id} ───────────────────────────────────────────────────────

@router.get("/{policy_id}", response_model=PolicyRuleResponse)
async def get_policy_rule(
    policy_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PolicyRuleResponse:
    """Get a single policy rule by ID."""
    candidate = await _get_candidate_or_404(db, current_user)
    rule = await _get_policy_for_candidate(db, policy_id, candidate.id)
    return PolicyRuleResponse.model_validate(rule)


# ── PUT /policies/{id} ───────────────────────────────────────────────────────

@router.put("/{policy_id}", response_model=PolicyRuleResponse)
async def update_policy_rule(
    policy_id: uuid.UUID,
    payload: PolicyRuleUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PolicyRuleResponse:
    """Update a policy rule."""
    if payload.action is not None and payload.action not in VALID_ACTIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid action '{payload.action}'. Valid actions: {VALID_ACTIONS}",
        )

    candidate = await _get_candidate_or_404(db, current_user)
    rule = await _get_policy_for_candidate(db, policy_id, candidate.id)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)

    await db.flush()
    await db.refresh(rule)
    return PolicyRuleResponse.model_validate(rule)


# ── DELETE /policies/{id} ─────────────────────────────────────────────────────

@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy_rule(
    policy_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a policy rule."""
    candidate = await _get_candidate_or_404(db, current_user)
    rule = await _get_policy_for_candidate(db, policy_id, candidate.id)
    await db.delete(rule)
    await db.flush()
