"""CRUD for parent-defined priority rules.

Rules let parents teach Parently what to always flag as important
(e.g. sender contains 'principal') or never notify about
(e.g. subject contains 'fundraiser').
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from dependencies import get_current_user
from storage import get_db
from storage.models import DigestRule, User

router = APIRouter()
logger = logging.getLogger(__name__)

db = get_db()

VALID_RULE_TYPES = {"always_important", "never_notify", "tag"}
VALID_FIELDS = {"sender", "subject", "body"}


class RuleCreate(BaseModel):
    rule_type: str
    field: str
    pattern: str
    label: Optional[str] = None

    @field_validator("rule_type")
    @classmethod
    def check_rule_type(cls, v: str) -> str:
        if v not in VALID_RULE_TYPES:
            raise ValueError(f"rule_type must be one of {sorted(VALID_RULE_TYPES)}")
        return v

    @field_validator("field")
    @classmethod
    def check_field(cls, v: str) -> str:
        if v not in VALID_FIELDS:
            raise ValueError(f"field must be one of {sorted(VALID_FIELDS)}")
        return v

    @field_validator("pattern")
    @classmethod
    def check_pattern(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("pattern cannot be empty")
        return v


def _serialize_rule(r: DigestRule) -> Dict[str, Any]:
    return {
        "id": r.id,
        "rule_type": r.rule_type,
        "field": r.field,
        "pattern": r.pattern,
        "label": r.label,
        "created_at": r.created_at.isoformat(),
    }


@router.get("")
def list_rules(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """List all priority rules for the current user."""
    with db.session_scope() as session:
        rules = (
            session.query(DigestRule)
            .filter(DigestRule.user_id == current_user.id)
            .order_by(DigestRule.created_at.desc())
            .all()
        )
        return {
            "ok": True,
            "rules": [_serialize_rule(r) for r in rules],
        }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_rule(
    body: RuleCreate,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Create a new priority rule."""
    with db.session_scope() as session:
        rule = DigestRule(
            user_id=current_user.id,
            rule_type=body.rule_type,
            field=body.field,
            pattern=body.pattern,
            label=body.label,
        )
        session.add(rule)
        session.flush()
        rule_id = rule.id

    logger.info("Created rule %d for user %d", rule_id, current_user.id)
    return {"ok": True, "rule_id": rule_id}


@router.delete("/{rule_id}")
def delete_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Delete a priority rule."""
    with db.session_scope() as session:
        rule = session.query(DigestRule).filter(
            DigestRule.id == rule_id,
            DigestRule.user_id == current_user.id,
        ).first()
        if not rule:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
        session.delete(rule)

    return {"ok": True}
