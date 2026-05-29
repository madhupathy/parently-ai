# Cost-capped free tier + $5/mo subscription — design

Date: 2026-05-29
Status: DRAFT — needs sign-off before wiring Stripe

## What we're changing

Today:
- Free = 30 lifetime digests, then HTTP 402.
- Premium = $3/mo unlimited (one Stripe `STRIPE_PRICE_ID`, README says $3, `dependencies.py:127` says $3).

Target:
- Free = **every feature, no digest-count cap**, gated only by a **$5.00 lifetime LLM cost cap**.
- Paid = **$5.00 / month**, unlimited, single plan.
- When a free user's accumulated LLM cost crosses $5.00 they get HTTP 402 with an upgrade prompt. Subscribing flips them to unlimited (lifetime cost still tracked for billing transparency but no longer gates).

This is a meaningful product change. Two reasons it makes sense:
1. The current 30-digest cap punishes users who run many small refresh digests; some legitimate users hit it the first week.
2. A cost-based cap is *honest* — it tracks what Parently actually spends serving you, and the conversion ask matches the cost we're trying to recover.

## Schema changes

Add two columns to `user_entitlements`. Keep `digests_remaining` for back-compat (we'll stop reading it but won't drop the column in the same migration — safer for rollback).

```sql
ALTER TABLE user_entitlements
  ADD COLUMN lifetime_cost_usd_cents INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN cost_cap_usd_cents     INTEGER NOT NULL DEFAULT 500;
```

A draft Alembic revision file lives at `apps/backend/alembic/versions/d4e5f6a7b8c9_cost_capped_entitlements.py` (added in this design pass — see below).

Why cents (integer) over float dollars: avoids accumulator drift. LLM cost per call is already a float in `LLMUsage.estimated_cost_usd`; we'll round each charge to cents before adding to the counter.

## Cost accrual

The pipeline already writes one `LLMUsage` row per LLM call (`apps/backend/storage/models.py:359`). We add a small service:

```python
# apps/backend/services/usage_meter.py
def record_llm_cost(user_id: int, cost_usd: float) -> None:
    """Add a cost to the user's lifetime accumulator. Called after every LLM call."""
    cents = max(0, round(cost_usd * 100))
    with db.session_scope() as session:
        ent = session.query(UserEntitlement).filter(
            UserEntitlement.user_id == user_id
        ).first()
        if not ent:
            return
        ent.lifetime_cost_usd_cents += cents
```

Hook this in the one place that writes `LLMUsage` rows — search for `session.add(LLMUsage(` in `apps/backend/agents/` and call `record_llm_cost` next to it.

## Gate logic

Replace `check_digest_entitlement` in `apps/backend/dependencies.py:104`:

```python
def check_digest_entitlement(current_user: User = Depends(get_current_user)) -> User:
    with db.session_scope() as session:
        ent = session.query(UserEntitlement).filter(
            UserEntitlement.user_id == current_user.id
        ).first()
        if not ent:
            ent = UserEntitlement(user_id=current_user.id, plan="FREE")
            session.add(ent)
            session.flush()
        if ent.premium_active:
            return current_user
        if ent.lifetime_cost_usd_cents < ent.cost_cap_usd_cents:
            return current_user
        raise HTTPException(
            status_code=402,
            detail={
                "error": "free_cost_cap_reached",
                "lifetime_cost_usd": ent.lifetime_cost_usd_cents / 100,
                "cap_usd": ent.cost_cap_usd_cents / 100,
                "message": "You've used your free $5 of LLM credit. Subscribe for $5/month for unlimited digests.",
            },
        )
```

Note: gate is checked *before* the digest run, but cost is accrued *during* the run. A user can therefore briefly exceed the cap by the cost of one in-flight digest. That's acceptable (the typical per-digest cost is well under $0.50 with Gemini Flash). If we want to be strict, we can do a post-run check and refund-not-count, but I'd skip that complexity for v1.

## Stripe changes

1. In Stripe Dashboard: create a new product "Parently — $5/month" with one recurring price at $5.00 USD/month. Take the new `price_xxx` and set `STRIPE_PRICE_ID` on the backend service.
2. Keep the old $3 price ID alive but stop pointing at it. Existing subscribers on the $3 price are grandfathered until they cancel and re-subscribe.
3. In `apps/backend/routers/billing.py:67` docstring + `apps/backend/dependencies.py:127` error message, update "$3" → "$5".
4. README "Plans and Pricing" table needs updating.

Code changes for Stripe are mechanical — the existing `create_checkout_session` already reads `settings.stripe_price_id`, so the swap is a single env var change. No code change is required to swap prices.

## What free-tier-for-all-features means in practice

Audit pass through the codebase for spots that *currently* gate features by `entitlement.plan == "PREMIUM"`:

| File | Line | Current behavior | New behavior |
|---|---|---|---|
| `apps/backend/dependencies.py` | 104-129 | gates digest run by `digests_remaining` | gate by `lifetime_cost_usd_cents` |
| `apps/backend/routers/digest.py` (history) | search for `lookback_days` / "7 days" / `premium_active` | history capped at 7 days for FREE | unlimited history for everyone |
| `apps/web/app/pricing/page.tsx` | — | UI lists feature differences between FREE and PREMIUM | only difference now: unlimited LLM usage |

The full audit needs ~30 minutes of reading. I'd handle it in the implementation PR, not here.

## What I'm NOT building in this pass

- **No live Stripe price change** — that needs your Stripe credentials.
- **No webhook update** — `billing.py` webhook handlers don't need changes; subscription status mapping is plan-agnostic.
- **No price-migration emails** — if you have existing $3/mo subscribers, they need a heads-up before any price change. That's a customer-comms task, not code.
- **No usage dashboard for users** — would be nice ("you've used $1.23 of $5") but is out of scope for this design.

## Test plan when implemented

1. New free user → can generate digests until `lifetime_cost_usd_cents >= 500`, then 402.
2. Free user with `lifetime_cost_usd_cents = 500` who subscribes → next digest runs (premium_active gate passes).
3. Subscription cancelled mid-month → at end of period, premium_active flips to false; if `lifetime_cost_usd_cents >= cost_cap_usd_cents`, they get 402 on next run.
4. Backfill: existing users with `digests_remaining = 0` should NOT be auto-blocked; they get a fresh $5 cap. Migration sets `lifetime_cost_usd_cents = 0` for everyone, so they get a fresh start. That's a deliberate choice; flag if you'd rather grandfather their old quota.
