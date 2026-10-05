"""
CareerOS - Policy Engine (Phase 6).

Evaluates whether an autonomous action is permitted given the candidate's policy rules.

Also implements:
- Prompt injection defense: sanitises LLM-bound strings
- Audit log service: records every significant event
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy import AuditLog, PolicyRule

log = structlog.get_logger(__name__)


# ── Prompt injection defense ─────────────────────────────────────────────────

# Patterns that suggest prompt injection attempts
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"you\s+are\s+now\s+a?\s+\w+",
    r"forget\s+(everything|all)\s+(you\s+)?(know|were told)",
    r"new\s+system\s+prompt",
    r"act\s+as\s+(if\s+you\s+are|a)\s+",
    r"disregard\s+(all\s+)?(previous|prior)\s+(instructions?|context)",
    r"jailbreak",
    r"\[SYSTEM\]",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"###\s*instruction",
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]

# Max length for any LLM-bound string
MAX_LLM_INPUT_LENGTH = 4000


def sanitise_for_llm(text: str, field_name: str = "input") -> str:
    """
    Sanitise a string before passing it to an LLM.

    Steps:
    1. Truncate to MAX_LLM_INPUT_LENGTH
    2. Detect and remove known injection patterns
    3. Log a warning if patterns were found

    Returns the sanitised string.
    """
    if not text:
        return text

    # Truncate
    if len(text) > MAX_LLM_INPUT_LENGTH:
        log.warning("policy.llm_input_truncated", field=field_name, original_len=len(text))
        text = text[:MAX_LLM_INPUT_LENGTH]

    # Detect injection
    for pattern in _COMPILED_PATTERNS:
        match = pattern.search(text)
        if match:
            log.warning(
                "policy.prompt_injection_detected",
                field=field_name,
                matched=match.group(0),
            )
            # Remove the injection attempt
            text = pattern.sub("[REDACTED]", text)

    return text


def check_for_injection(text: str) -> bool:
    """Return True if the text contains a suspected injection attempt."""
    if not text:
        return False
    return any(p.search(text) for p in _COMPILED_PATTERNS)


# ── Policy evaluation ─────────────────────────────────────────────────────────

class PolicyDecision:
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


class PolicyEvaluationResult:
    """Result of evaluating a policy rule for an action."""

    def __init__(
        self,
        decision: str,
        rule: Optional[PolicyRule] = None,
        reason: str = "",
    ):
        self.decision = decision
        self.rule = rule
        self.reason = reason

    @property
    def allowed(self) -> bool:
        return self.decision in (PolicyDecision.ALLOW, PolicyDecision.REQUIRE_APPROVAL)

    @property
    def needs_approval(self) -> bool:
        return self.decision == PolicyDecision.REQUIRE_APPROVAL


async def evaluate_policy(
    db: AsyncSession,
    candidate_id: uuid.UUID,
    action: str,
    context: Optional[Dict[str, Any]] = None,
) -> PolicyEvaluationResult:
    """
    Evaluate whether an action is permitted for a candidate.

    Logic:
    1. Look up PolicyRule for this candidate + action
    2. If rule found: use its settings
    3. If no rule: default to require_approval (safe default)
    4. Evaluate any conditions against context

    Returns PolicyEvaluationResult.
    """
    result = await db.execute(
        select(PolicyRule).where(
            and_(
                PolicyRule.candidate_id == candidate_id,
                PolicyRule.action == action,
            )
        )
    )
    rule = result.scalar_one_or_none()

    if not rule:
        # No rule = default: require approval (conservative)
        return PolicyEvaluationResult(
            decision=PolicyDecision.REQUIRE_APPROVAL,
            reason=f"No policy rule for action '{action}' — defaulting to require_approval",
        )

    if not rule.enabled:
        return PolicyEvaluationResult(
            decision=PolicyDecision.DENY,
            rule=rule,
            reason=f"Action '{action}' is disabled by policy",
        )

    # Evaluate conditions if present
    if rule.conditions and context:
        try:
            conditions = json.loads(rule.conditions)
            for key, required_value in conditions.items():
                actual_value = context.get(key)
                if actual_value is None:
                    continue
                if isinstance(required_value, (int, float)) and isinstance(actual_value, (int, float)):
                    if actual_value < required_value:
                        return PolicyEvaluationResult(
                            decision=PolicyDecision.DENY,
                            rule=rule,
                            reason=f"Condition '{key}' not met: {actual_value} < {required_value}",
                        )
                elif actual_value != required_value:
                    return PolicyEvaluationResult(
                        decision=PolicyDecision.DENY,
                        rule=rule,
                        reason=f"Condition '{key}' not met: {actual_value} != {required_value}",
                    )
        except (json.JSONDecodeError, TypeError):
            pass

    if rule.requires_approval:
        return PolicyEvaluationResult(
            decision=PolicyDecision.REQUIRE_APPROVAL,
            rule=rule,
            reason="Policy requires human approval for this action",
        )

    return PolicyEvaluationResult(
        decision=PolicyDecision.ALLOW,
        rule=rule,
        reason="Action permitted by policy",
    )


# ── Audit log service ─────────────────────────────────────────────────────────

async def audit(
    db: AsyncSession,
    action: str,
    *,
    user_id: Optional[uuid.UUID] = None,
    candidate_id: Optional[uuid.UUID] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    correlation_id: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None,
) -> AuditLog:
    """
    Write an immutable audit log entry.

    Should be called for every significant state change:
    - application.create, application.approve, application.submit
    - resume.generate
    - email.send
    - policy.update
    """
    entry = AuditLog(
        user_id=user_id,
        candidate_id=candidate_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None,
        details=json.dumps(details) if details else None,
        ip_address=ip_address,
        user_agent=user_agent,
        correlation_id=correlation_id,
        success=success,
        error_message=error_message,
    )
    db.add(entry)
    await db.flush()
    log.info("audit.logged", action=action, success=success, resource_type=resource_type)
    return entry


async def get_audit_logs(
    db: AsyncSession,
    candidate_id: Optional[uuid.UUID] = None,
    action: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[AuditLog], int]:
    """Query audit logs with optional filters."""
    from sqlalchemy import func

    conditions = []
    if candidate_id:
        conditions.append(AuditLog.candidate_id == candidate_id)
    if action:
        conditions.append(AuditLog.action == action)

    count_q = select(func.count()).select_from(AuditLog)
    if conditions:
        count_q = count_q.where(and_(*conditions))
    total = (await db.execute(count_q)).scalar_one()

    q = select(AuditLog).order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    if conditions:
        q = q.where(and_(*conditions))
    logs = list((await db.execute(q)).scalars().all())
    return logs, total
