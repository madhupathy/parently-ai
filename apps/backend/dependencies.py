"""Shared FastAPI dependencies."""

from __future__ import annotations

import logging
from typing import Annotated, Optional

import jwt
from fastapi import Depends, Header, HTTPException, status

from config import get_settings
from storage import get_db
from storage.models import User, UserEntitlement

logger = logging.getLogger(__name__)


def _decode_jwt(token: str) -> dict:
    """Decode a NextAuth HS256 JWT using the shared NEXTAUTH_SECRET."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.nextauth_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError as exc:
        logger.warning("JWT decode failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_current_user(
    authorization: Annotated[str, Header(..., alias="authorization")]
) -> User:
    """Extract and verify JWT from Authorization header, return User (create if needed)."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")

    token = authorization[7:]
    payload = _decode_jwt(token)

    email = payload.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing email")

    name = payload.get("name")
    provider = payload.get("provider", "google")

    db = get_db()
    with db.session_scope() as session:
        user = session.query(User).filter(User.email == email).first()
        if not user:
            user = User(email=email, name=name, provider=provider)
            session.add(user)
            session.flush()
            entitlement = UserEntitlement(user_id=user.id, plan="FREE", digests_remaining=30)
            session.add(entitlement)
            session.flush()
            logger.info("Created new user %s (id=%d) with FREE entitlement", email, user.id)
        else:
            if name and name != user.name:
                user.name = name

        # Detach-safe: copy attributes before session closes
        user_id = user.id
        user_email = user.email
        user_name = user.name
        user_provider = user.provider
        user_avatar = user.avatar_url

    # Return a transient User object usable outside the session
    detached = User(
        id=user_id,
        email=user_email,
        name=user_name,
        provider=user_provider,
        avatar_url=user_avatar,
    )
    # Prevent SQLAlchemy from treating this as a new insert
    from sqlalchemy.orm import make_transient
    make_transient(detached)
    detached.id = user_id
    return detached


def verify_cron_secret(
    x_cron_secret: Annotated[str, Header(..., alias="x-cron-secret")]
) -> str:
    """Verify internal cron endpoint secret."""
    settings = get_settings()
    if not settings.cron_secret or x_cron_secret != settings.cron_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid cron secret")
    return x_cron_secret


def check_digest_entitlement(current_user: User = Depends(get_current_user)) -> User:
    """Check if user can generate a digest. Returns user if allowed, else 402."""
    db = get_db()
    with db.session_scope() as session:
        entitlement = session.query(UserEntitlement).filter(
            UserEntitlement.user_id == current_user.id
        ).first()

        if not entitlement:
            entitlement = UserEntitlement(user_id=current_user.id, plan="FREE", digests_remaining=30)
            session.add(entitlement)
            session.flush()

        if entitlement.premium_active:
            return current_user

        if entitlement.digests_remaining > 0:
            return current_user

        raise HTTPException(
            status_code=402,
            detail={
                "error": "free_limit_reached",
                "message": "Free digest limit reached. Subscribe for $3/month for unlimited digests.",
            },
        )
