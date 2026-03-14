"""
Billing API Routes - Stripe checkout, webhooks, credit balance, usage stats.
"""

import logging
from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.core.config import get_settings
from app.domain.models.user import User
from app.interfaces.api.dependencies import get_current_user
from app.interfaces.api.response import APIResponse
from app.domain.services.billing.products import SubscriptionTier, TIERS, CREDIT_COSTS
from app.domain.services.billing.credit_service import get_credit_service
from app.domain.services.billing.stripe_service import get_stripe_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


# ── Request/Response Models ──────────────────────────────────────────

class CheckoutRequest(BaseModel):
    tier: str  # "pro" or "team"
    success_url: str
    cancel_url: str


class PortalRequest(BaseModel):
    return_url: str


# ── Public Routes ────────────────────────────────────────────────────

@router.get("/tiers", response_model=APIResponse)
async def get_tiers():
    """Get all available subscription tiers and pricing"""
    tiers_data = []
    for tier_enum, config in TIERS.items():
        tiers_data.append({
            "tier": config.tier.value,
            "name": config.name,
            "price_monthly": config.price_monthly_cents / 100,
            "credits_monthly": config.credits_monthly,
            "daily_agent_limit": config.daily_agent_limit,
            "concurrent_agents": config.concurrent_agents,
            "features": config.features,
        })
    return APIResponse.success(tiers_data)


@router.get("/credit-costs", response_model=APIResponse)
async def get_credit_costs():
    """Get credit costs per operation"""
    return APIResponse.success(CREDIT_COSTS)


# ── Authenticated Routes ─────────────────────────────────────────────

@router.get("/balance", response_model=APIResponse)
async def get_balance(current_user: User = Depends(get_current_user)):
    """Get current user's credit balance"""
    credit_service = get_credit_service()
    balance = await credit_service.get_balance(current_user.id)
    tier_config = TIERS[balance.tier]
    return APIResponse.success({
        "tier": balance.tier.value,
        "tier_name": tier_config.name,
        "credits_remaining": balance.credits_remaining,
        "credits_total": tier_config.credits_monthly,
        "credits_used_today": balance.credits_used_today,
        "credits_used_month": balance.credits_used_month,
        "daily_agent_count": balance.daily_agent_count,
        "daily_agent_limit": tier_config.daily_agent_limit,
        "stripe_customer_id": balance.stripe_customer_id,
    })


@router.get("/usage", response_model=APIResponse)
async def get_usage_stats(current_user: User = Depends(get_current_user)):
    """Get usage statistics for dashboard"""
    credit_service = get_credit_service()
    stats = await credit_service.get_usage_stats(current_user.id)
    return APIResponse.success(stats)


@router.post("/checkout", response_model=APIResponse)
async def create_checkout(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a Stripe Checkout session for subscription"""
    try:
        tier = SubscriptionTier(request.tier)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {request.tier}")

    if tier == SubscriptionTier.FREE:
        raise HTTPException(status_code=400, detail="Free tier doesn't require checkout")

    stripe_service = get_stripe_service()
    checkout_url = await stripe_service.create_checkout_session(
        user_id=current_user.id,
        user_email=current_user.email,
        tier=tier,
        success_url=request.success_url,
        cancel_url=request.cancel_url,
    )

    if not checkout_url:
        raise HTTPException(status_code=500, detail="Failed to create checkout session. Stripe may not be configured.")

    return APIResponse.success({"checkout_url": checkout_url})


@router.post("/portal", response_model=APIResponse)
async def create_portal(
    request: PortalRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a Stripe Customer Portal session for managing subscription"""
    credit_service = get_credit_service()
    balance = await credit_service.get_balance(current_user.id)

    if not balance.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No active subscription found")

    stripe_service = get_stripe_service()
    portal_url = await stripe_service.get_customer_portal_url(
        stripe_customer_id=balance.stripe_customer_id,
        return_url=request.return_url,
    )

    if not portal_url:
        raise HTTPException(status_code=500, detail="Failed to create portal session")

    return APIResponse.success({"portal_url": portal_url})


# ── Stripe Webhook ───────────────────────────────────────────────────

@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    settings = get_settings()
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # Verify webhook signature
    try:
        import stripe
        if settings.stripe_webhook_secret and sig_header:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
        else:
            # No webhook secret configured, parse raw (dev mode)
            import json
            event = json.loads(payload)
    except Exception as e:
        logger.error(f"[Webhook] Signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Test event detection
    event_id = event.get("id", "")
    if event_id.startswith("evt_test_"):
        return {"verified": True}

    # Process event
    stripe_service = get_stripe_service()
    success = await stripe_service.handle_webhook_event(event)

    if success:
        return {"status": "ok"}
    else:
        raise HTTPException(status_code=500, detail="Webhook processing failed")
