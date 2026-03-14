"""
Product and pricing definitions.
Stripe products/prices are created on first use and cached.
"""

from enum import Enum
from pydantic import BaseModel
from typing import Optional


class SubscriptionTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    TEAM = "team"


class TierConfig(BaseModel):
    """Configuration for a subscription tier"""
    name: str
    tier: SubscriptionTier
    price_monthly_cents: int  # in cents (USD)
    credits_monthly: int
    daily_agent_limit: int  # max agent tasks per day
    concurrent_agents: int  # max concurrent agent sessions
    features: list[str]
    stripe_price_id: Optional[str] = None  # Set after Stripe product creation


# Tier definitions
TIERS: dict[SubscriptionTier, TierConfig] = {
    SubscriptionTier.FREE: TierConfig(
        name="Free",
        tier=SubscriptionTier.FREE,
        price_monthly_cents=0,
        credits_monthly=50,  # 50 credits/day = ~5 agent tasks
        daily_agent_limit=5,
        concurrent_agents=1,
        features=[
            "5 Agent tasks/day",
            "Basic chat",
            "Community support",
        ],
    ),
    SubscriptionTier.PRO: TierConfig(
        name="Pro",
        tier=SubscriptionTier.PRO,
        price_monthly_cents=1990,  # $19.90/month
        credits_monthly=2000,
        daily_agent_limit=100,
        concurrent_agents=3,
        features=[
            "100 Agent tasks/day",
            "Browser preview",
            "File management",
            "Priority support",
            "SOVR trust dashboard",
        ],
    ),
    SubscriptionTier.TEAM: TierConfig(
        name="Team",
        tier=SubscriptionTier.TEAM,
        price_monthly_cents=4990,  # $49.90/month/seat
        credits_monthly=10000,
        daily_agent_limit=-1,  # unlimited
        concurrent_agents=10,
        features=[
            "Unlimited Agent tasks",
            "SOVR full audit trail",
            "Team collaboration",
            "Admin dashboard",
            "API access",
            "Dedicated support",
        ],
    ),
}


# Credit costs per operation
CREDIT_COSTS = {
    "agent_task": 10,       # 1 Agent task = 10 credits
    "chat_message": 1,      # 1 chat message = 1 credit
    "image_generation": 5,  # 1 image = 5 credits
}


# Stripe product metadata
PRODUCTS = {
    "pro_monthly": {
        "name": "SOVR AI Agent Pro - Monthly",
        "description": "Professional AI Agent platform with SOVR trust layer",
        "tier": SubscriptionTier.PRO,
        "interval": "month",
    },
    "team_monthly": {
        "name": "SOVR AI Agent Team - Monthly",
        "description": "Team AI Agent platform with full SOVR audit and collaboration",
        "tier": SubscriptionTier.TEAM,
        "interval": "month",
    },
}
