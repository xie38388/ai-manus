"""
Credit Service - Manages user credit balances and consumption.
Uses MongoDB for persistence via Beanie ODM.
"""

import logging
from datetime import datetime, UTC, timedelta
from typing import Optional
from pydantic import BaseModel

from app.domain.services.billing.products import (
    SubscriptionTier, TIERS, CREDIT_COSTS
)

logger = logging.getLogger(__name__)


class CreditBalance(BaseModel):
    """User's current credit state"""
    user_id: str
    tier: SubscriptionTier = SubscriptionTier.FREE
    credits_remaining: int = 0
    credits_used_today: int = 0
    credits_used_month: int = 0
    daily_agent_count: int = 0
    last_reset_date: str = ""  # YYYY-MM-DD
    month_reset_date: str = ""  # YYYY-MM
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None


class CreditCheckResult(BaseModel):
    """Result of a credit check"""
    allowed: bool
    reason: str = ""
    credits_required: int = 0
    credits_remaining: int = 0
    daily_agent_remaining: int = -1


class CreditService:
    """
    Manages credit balances in-memory with MongoDB persistence.
    For now, uses a simple dict cache; in production, use Redis.
    """

    def __init__(self):
        self._balances: dict[str, CreditBalance] = {}

    async def get_balance(self, user_id: str) -> CreditBalance:
        """Get or create a user's credit balance"""
        if user_id not in self._balances:
            # In production, load from MongoDB
            self._balances[user_id] = CreditBalance(
                user_id=user_id,
                tier=SubscriptionTier.FREE,
                credits_remaining=TIERS[SubscriptionTier.FREE].credits_monthly,
                last_reset_date=datetime.now(UTC).strftime("%Y-%m-%d"),
                month_reset_date=datetime.now(UTC).strftime("%Y-%m"),
            )
        
        balance = self._balances[user_id]
        self._check_daily_reset(balance)
        self._check_monthly_reset(balance)
        return balance

    def _check_daily_reset(self, balance: CreditBalance):
        """Reset daily counters if new day"""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        if balance.last_reset_date != today:
            balance.credits_used_today = 0
            balance.daily_agent_count = 0
            balance.last_reset_date = today

    def _check_monthly_reset(self, balance: CreditBalance):
        """Reset monthly credits if new month"""
        this_month = datetime.now(UTC).strftime("%Y-%m")
        if balance.month_reset_date != this_month:
            tier_config = TIERS[balance.tier]
            balance.credits_remaining = tier_config.credits_monthly
            balance.credits_used_month = 0
            balance.month_reset_date = this_month

    async def check_credits(
        self, user_id: str, operation: str
    ) -> CreditCheckResult:
        """Check if user has enough credits for an operation"""
        balance = await self.get_balance(user_id)
        tier_config = TIERS[balance.tier]
        cost = CREDIT_COSTS.get(operation, 1)

        # Check daily agent limit
        if operation == "agent_task":
            daily_limit = tier_config.daily_agent_limit
            if daily_limit > 0 and balance.daily_agent_count >= daily_limit:
                return CreditCheckResult(
                    allowed=False,
                    reason=f"Daily agent task limit reached ({daily_limit}/day). Upgrade to increase.",
                    credits_required=cost,
                    credits_remaining=balance.credits_remaining,
                    daily_agent_remaining=0,
                )

        # Check credit balance
        if balance.credits_remaining < cost:
            return CreditCheckResult(
                allowed=False,
                reason=f"Insufficient credits. Need {cost}, have {balance.credits_remaining}. Upgrade or wait for monthly reset.",
                credits_required=cost,
                credits_remaining=balance.credits_remaining,
            )

        daily_remaining = -1
        if operation == "agent_task" and tier_config.daily_agent_limit > 0:
            daily_remaining = tier_config.daily_agent_limit - balance.daily_agent_count

        return CreditCheckResult(
            allowed=True,
            credits_required=cost,
            credits_remaining=balance.credits_remaining,
            daily_agent_remaining=daily_remaining,
        )

    async def consume_credits(
        self, user_id: str, operation: str, amount: Optional[int] = None
    ) -> CreditBalance:
        """Deduct credits for an operation"""
        balance = await self.get_balance(user_id)
        cost = amount if amount is not None else CREDIT_COSTS.get(operation, 1)

        balance.credits_remaining = max(0, balance.credits_remaining - cost)
        balance.credits_used_today += cost
        balance.credits_used_month += cost

        if operation == "agent_task":
            balance.daily_agent_count += 1

        logger.info(
            f"[Credit] User {user_id}: -{cost} credits for {operation}, "
            f"remaining={balance.credits_remaining}"
        )
        return balance

    async def set_tier(
        self, user_id: str, tier: SubscriptionTier,
        stripe_customer_id: Optional[str] = None,
        stripe_subscription_id: Optional[str] = None,
    ) -> CreditBalance:
        """Update user's subscription tier (called after Stripe webhook)"""
        balance = await self.get_balance(user_id)
        old_tier = balance.tier
        balance.tier = tier

        if stripe_customer_id:
            balance.stripe_customer_id = stripe_customer_id
        if stripe_subscription_id:
            balance.stripe_subscription_id = stripe_subscription_id

        # If upgrading, add the difference in credits
        if tier != old_tier:
            new_config = TIERS[tier]
            old_config = TIERS[old_tier]
            credit_diff = new_config.credits_monthly - old_config.credits_monthly
            if credit_diff > 0:
                balance.credits_remaining += credit_diff

        logger.info(
            f"[Credit] User {user_id}: tier changed {old_tier} → {tier}, "
            f"credits={balance.credits_remaining}"
        )
        return balance

    async def add_credits(self, user_id: str, amount: int) -> CreditBalance:
        """Add credits to user (e.g., bonus, purchase)"""
        balance = await self.get_balance(user_id)
        balance.credits_remaining += amount
        logger.info(
            f"[Credit] User {user_id}: +{amount} credits, "
            f"remaining={balance.credits_remaining}"
        )
        return balance

    async def get_usage_stats(self, user_id: str) -> dict:
        """Get usage statistics for dashboard"""
        balance = await self.get_balance(user_id)
        tier_config = TIERS[balance.tier]
        return {
            "tier": balance.tier.value,
            "tier_name": tier_config.name,
            "credits_remaining": balance.credits_remaining,
            "credits_total": tier_config.credits_monthly,
            "credits_used_today": balance.credits_used_today,
            "credits_used_month": balance.credits_used_month,
            "daily_agent_count": balance.daily_agent_count,
            "daily_agent_limit": tier_config.daily_agent_limit,
            "concurrent_agents": tier_config.concurrent_agents,
            "usage_percent": round(
                (balance.credits_used_month / tier_config.credits_monthly * 100)
                if tier_config.credits_monthly > 0 else 0, 1
            ),
        }


# Singleton instance
_credit_service: Optional[CreditService] = None


def get_credit_service() -> CreditService:
    global _credit_service
    if _credit_service is None:
        _credit_service = CreditService()
    return _credit_service
