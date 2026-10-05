"""
CareerOS - Audit log API endpoints (Phase 8).

Audit logs are READ-ONLY. No create/update/delete via API.

Routes:
  GET  /audit/      - list audit logs for current user (paginated, filterable)
  GET  /audit/{id}  - get single audit log entry
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.policy import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogListResponse, AuditLogResponse

router = APIRouter()


# ── GET /audit/ ───────────────────────────────────────────────────────────────

@router.get("/", response_model=AuditLogListResponse)
async def list_audit_logs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    action: Optional[str] = Query(default=None, description="Filter by action name"),
    resource_type: Optional[str] = Query(default=None, description="Filter by resource type"),
    date_from: Optional[datetime] = Query(default=None, description="Filter from this datetime (ISO 8601)"),
    date_to: Optional[datetime] = Query(default=None, description="Filter to this datetime (ISO 8601)"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> AuditLogListResponse:
    """
    List audit log entries for the current user.
    Supports filtering by action, resource_type, and date range.
    """
    conditions = [AuditLog.user_id == current_user.id]

    if action is not None:
        conditions.append(AuditLog.action == action)
    if resource_type is not None:
        conditions.append(AuditLog.resource_type == resource_type)
    if date_from is not None:
        conditions.append(AuditLog.created_at >= date_from)
    if date_to is not None:
        conditions.append(AuditLog.created_at <= date_to)

    where_clause = and_(*conditions)

    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(AuditLog).where(where_clause)
    )
    total = count_result.scalar_one()

    # Fetch page
    offset = (page - 1) * page_size
    result = await db.execute(
        select(AuditLog)
        .where(where_clause)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    logs = result.scalars().all()

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── GET /audit/{id} ───────────────────────────────────────────────────────────

@router.get("/{audit_id}", response_model=AuditLogResponse)
async def get_audit_log(
    audit_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuditLogResponse:
    """Get a single audit log entry by ID. Only returns entries belonging to current user."""
    result = await db.execute(
        select(AuditLog).where(
            AuditLog.id == audit_id,
            AuditLog.user_id == current_user.id,
        )
    )
    log_entry = result.scalar_one_or_none()
    if not log_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log entry not found",
        )
    return AuditLogResponse.model_validate(log_entry)
