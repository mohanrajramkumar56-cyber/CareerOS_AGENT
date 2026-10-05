"""
CareerOS - Policy rule Pydantic schemas.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PolicyRuleCreate(BaseModel):
    action: str = Field(..., max_length=200)
    enabled: bool = True
    requires_approval: bool = True
    max_per_day: Optional[int] = Field(default=None, ge=1)
    max_per_week: Optional[int] = Field(default=None, ge=1)
    conditions: Optional[str] = None  # JSON string
    description: Optional[str] = None


class PolicyRuleUpdate(BaseModel):
    action: Optional[str] = Field(default=None, max_length=200)
    enabled: Optional[bool] = None
    requires_approval: Optional[bool] = None
    max_per_day: Optional[int] = Field(default=None, ge=1)
    max_per_week: Optional[int] = Field(default=None, ge=1)
    conditions: Optional[str] = None
    description: Optional[str] = None


class PolicyRuleResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    action: str
    enabled: bool
    requires_approval: bool
    max_per_day: Optional[int]
    max_per_week: Optional[int]
    conditions: Optional[str]
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
