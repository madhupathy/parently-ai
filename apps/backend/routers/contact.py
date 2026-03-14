"""Public contact form endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.email_service import send_support_request_email

router = APIRouter()


class ContactRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=320)
    message: str = Field(min_length=10, max_length=5000)


@router.post("")
def submit_contact(payload: ContactRequest):
    if "@" not in payload.email:
        raise HTTPException(status_code=400, detail="Please enter a valid email address")

    sent = send_support_request_email(
        name=payload.name.strip(),
        email=payload.email.strip(),
        message=payload.message.strip(),
    )

    if not sent:
        raise HTTPException(
            status_code=503,
            detail="Support email is temporarily unavailable. Please try again later.",
        )

    return {"ok": True, "message": "Thanks for contacting us. We will reply soon."}
