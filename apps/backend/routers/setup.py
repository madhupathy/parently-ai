"""Setup status routes."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from dependencies import get_current_user
from services.setup_status import compute_setup_status
from storage.models import User

router = APIRouter()


@router.get("/status")
def setup_status(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    return {"ok": True, "setup_status": compute_setup_status(current_user.id)}
