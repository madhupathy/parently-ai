"""Children CRUD routes."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from dependencies import get_current_user
from storage import get_db
from storage.models import Child, User

router = APIRouter()
logger = logging.getLogger(__name__)

db = get_db()


class ChildCreate(BaseModel):
    name: str
    grade: Optional[str] = None
    school_name: Optional[str] = None
    school_domain: Optional[str] = None
    teacher_name: Optional[str] = None
    birthdate: Optional[str] = None


class ChildUpdate(BaseModel):
    name: Optional[str] = None
    grade: Optional[str] = None
    school_name: Optional[str] = None
    school_domain: Optional[str] = None
    teacher_name: Optional[str] = None
    birthdate: Optional[str] = None


@router.get("")
def list_children(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """List all children for the current user."""
    with db.session_scope() as session:
        children = session.query(Child).filter(Child.user_id == current_user.id).all()
        return {
            "ok": True,
            "children": [
                {
                    "id": c.id,
                    "name": c.name,
                    "grade": c.grade,
                    "school_name": c.school_name,
                    "school_domain": c.school_domain,
                    "teacher_name": c.teacher_name,
                    "birthdate": c.birthdate,
                    "photo_url": c.photo_url,
                }
                for c in children
            ],
        }


@router.post("")
def create_child(
    body: ChildCreate,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Add a child profile."""
    with db.session_scope() as session:
        child = Child(
            user_id=current_user.id,
            name=body.name,
            grade=body.grade,
            school_name=body.school_name,
            school_domain=body.school_domain,
            teacher_name=body.teacher_name,
            birthdate=body.birthdate,
        )
        session.add(child)
        session.flush()
        child_id = child.id

    logger.info("Created child %d for user %d", child_id, current_user.id)
    return {"ok": True, "child_id": child_id}


@router.put("/{child_id}")
def update_child(
    child_id: int,
    body: ChildUpdate,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Update a child profile."""
    with db.session_scope() as session:
        child = session.query(Child).filter(
            Child.id == child_id, Child.user_id == current_user.id
        ).first()
        if not child:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Child not found")

        if body.name is not None:
            child.name = body.name
        if body.grade is not None:
            child.grade = body.grade
        if body.school_name is not None:
            child.school_name = body.school_name
        if body.school_domain is not None:
            child.school_domain = body.school_domain
        if body.teacher_name is not None:
            child.teacher_name = body.teacher_name
        if body.birthdate is not None:
            child.birthdate = body.birthdate

    return {"ok": True}


@router.delete("/{child_id}")
def delete_child(
    child_id: int,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Remove a child profile."""
    with db.session_scope() as session:
        child = session.query(Child).filter(
            Child.id == child_id, Child.user_id == current_user.id
        ).first()
        if not child:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Child not found")
        session.delete(child)

    return {"ok": True}
