"""Billing routes — Stripe checkout + webhook + status."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict
from urllib.parse import urlparse

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status

from config import get_settings
from dependencies import get_current_user
from storage import get_db
from storage.models import StripeCustomer, User, UserEntitlement

router = APIRouter()
logger = logging.getLogger(__name__)

db = get_db()

def _resolve_checkout_urls(settings: Any) -> tuple[str, str]:
    configured = (settings.frontend_app_url or "").strip()
    fallback = "http://localhost:3000"
    base = configured or fallback
    parsed = urlparse(base)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        base = fallback
    base = base.rstrip("/")
    return (f"{base}/dashboard?upgraded=true", f"{base}/pricing")


@router.get("/status")
def billing_status(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Return the current user's billing status."""
    with db.session_scope() as session:
        entitlement = session.query(UserEntitlement).filter(
            UserEntitlement.user_id == current_user.id
        ).first()

        stripe_cust = session.query(StripeCustomer).filter(
            StripeCustomer.user_id == current_user.id
        ).first()

        return {
            "ok": True,
            "plan": entitlement.plan if entitlement else "FREE",
            "digests_remaining": entitlement.digests_remaining if entitlement else 2000,
            "premium_active": entitlement.premium_active if entitlement else False,
            "premium_started_at": (
                entitlement.premium_started_at.isoformat()
                if entitlement and entitlement.premium_started_at else None
            ),
            "premium_ends_at": (
                entitlement.premium_ends_at.isoformat()
                if entitlement and entitlement.premium_ends_at else None
            ),
            "stripe_subscription_id": (
                stripe_cust.stripe_subscription_id if stripe_cust else None
            ),
        }


@router.post("/create-checkout-session")
def create_checkout_session(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Create a Stripe Checkout session for $3/month premium subscription."""
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe secret key is not configured",
        )
    if not settings.stripe_price_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe price ID is not configured",
        )

    stripe.api_key = settings.stripe_secret_key

    # Get or create Stripe customer
    with db.session_scope() as session:
        stripe_cust = session.query(StripeCustomer).filter(
            StripeCustomer.user_id == current_user.id
        ).first()

        if stripe_cust:
            customer_id = stripe_cust.stripe_customer_id
        else:
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.name or "",
                metadata={"parently_user_id": str(current_user.id)},
            )
            customer_id = customer.id
            stripe_cust = StripeCustomer(
                user_id=current_user.id,
                stripe_customer_id=customer_id,
                status="inactive",
            )
            session.add(stripe_cust)
            session.flush()

    # Create checkout session
    success_url, cancel_url = _resolve_checkout_urls(settings)

    try:
        checkout = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{"price": settings.stripe_price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"parently_user_id": str(current_user.id)},
        )
    except Exception as exc:
        logger.error("Stripe checkout session creation failed for user %s: %s", current_user.id, exc)
        raise HTTPException(status_code=502, detail="Unable to create Stripe checkout session")

    return {"ok": True, "checkout_url": checkout.url}


@router.post("/webhook")
async def stripe_webhook(request: Request) -> Dict[str, Any]:
    """Handle Stripe webhook events for subscription lifecycle."""
    settings = get_settings()
    if not settings.stripe_secret_key or not settings.stripe_webhook_secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Stripe not configured")

    stripe.api_key = settings.stripe_secret_key

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        logger.warning("Stripe webhook signature verification failed")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as exc:
        logger.error("Stripe webhook error: %s", exc)
        raise HTTPException(status_code=400, detail="Webhook error")

    event_type = event["type"]
    data_object = event["data"]["object"]

    logger.info("Stripe webhook: %s", event_type)

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data_object)
    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(data_object)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(data_object)

    return {"ok": True}


def _handle_checkout_completed(session_obj: dict) -> None:
    """Activate premium after successful checkout."""
    customer_id = session_obj.get("customer")
    subscription_id = session_obj.get("subscription")

    if not customer_id:
        return

    with db.session_scope() as session:
        stripe_cust = session.query(StripeCustomer).filter(
            StripeCustomer.stripe_customer_id == customer_id
        ).first()
        if not stripe_cust:
            logger.warning("Checkout completed for unknown customer: %s", customer_id)
            return

        stripe_cust.stripe_subscription_id = subscription_id
        stripe_cust.status = "active"

        entitlement = session.query(UserEntitlement).filter(
            UserEntitlement.user_id == stripe_cust.user_id
        ).first()
        if entitlement:
            entitlement.plan = "PREMIUM"
            entitlement.premium_active = True
            entitlement.premium_started_at = datetime.utcnow()
            entitlement.premium_ends_at = None
        else:
            session.add(UserEntitlement(
                user_id=stripe_cust.user_id,
                plan="PREMIUM",
                digests_remaining=30,
                premium_active=True,
                premium_started_at=datetime.utcnow(),
            ))

    logger.info("Premium activated for customer %s", customer_id)


def _handle_subscription_updated(sub_obj: dict) -> None:
    """Handle subscription status changes (e.g., past_due, active)."""
    customer_id = sub_obj.get("customer")
    sub_status = sub_obj.get("status")

    if not customer_id:
        return

    with db.session_scope() as session:
        stripe_cust = session.query(StripeCustomer).filter(
            StripeCustomer.stripe_customer_id == customer_id
        ).first()
        if not stripe_cust:
            return

        stripe_cust.status = sub_status or "unknown"

        entitlement = session.query(UserEntitlement).filter(
            UserEntitlement.user_id == stripe_cust.user_id
        ).first()
        if entitlement:
            is_active = sub_status in ("active", "trialing")
            entitlement.premium_active = is_active
            if not is_active:
                entitlement.plan = "FREE"

    logger.info("Subscription updated for customer %s: %s", customer_id, sub_status)


def _handle_subscription_deleted(sub_obj: dict) -> None:
    """Deactivate premium when subscription is cancelled."""
    customer_id = sub_obj.get("customer")

    if not customer_id:
        return

    with db.session_scope() as session:
        stripe_cust = session.query(StripeCustomer).filter(
            StripeCustomer.stripe_customer_id == customer_id
        ).first()
        if not stripe_cust:
            return

        stripe_cust.status = "cancelled"

        entitlement = session.query(UserEntitlement).filter(
            UserEntitlement.user_id == stripe_cust.user_id
        ).first()
        if entitlement:
            entitlement.plan = "FREE"
            entitlement.premium_active = False
            entitlement.premium_ends_at = datetime.utcnow()

    logger.info("Subscription deleted for customer %s", customer_id)
