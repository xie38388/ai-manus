"""
Stripe Service - Handles checkout sessions, webhooks, and subscription management.
"""

import logging
from typing import Optional

from app.core.config import get_settings
from app.domain.services.billing.products import (
    SubscriptionTier, TIERS, PRODUCTS
)
from app.domain.services.billing.credit_service import get_credit_service

logger = logging.getLogger(__name__)

# Lazy import stripe to avoid import errors when not configured
_stripe = None


def _get_stripe():
    global _stripe
    if _stripe is None:
        try:
            import stripe
            settings = get_settings()
            if settings.stripe_secret_key:
                stripe.api_key = settings.stripe_secret_key
                _stripe = stripe
                logger.info("[Stripe] Initialized with secret key")
            else:
                logger.warning("[Stripe] No secret key configured, Stripe disabled")
        except ImportError:
            logger.warning("[Stripe] stripe package not installed")
    return _stripe


class StripeService:
    """Manages Stripe integration for subscriptions"""

    def __init__(self):
        self._price_cache: dict[str, str] = {}  # tier -> stripe_price_id

    async def create_checkout_session(
        self,
        user_id: str,
        user_email: str,
        tier: SubscriptionTier,
        success_url: str,
        cancel_url: str,
    ) -> Optional[str]:
        """Create a Stripe Checkout Session and return the URL"""
        stripe = _get_stripe()
        if not stripe:
            logger.error("[Stripe] Not configured")
            return None

        if tier == SubscriptionTier.FREE:
            return None  # Free tier doesn't need checkout

        # Get or create the price
        price_id = await self._ensure_price(tier)
        if not price_id:
            return None

        try:
            session = stripe.checkout.Session.create(
                mode="subscription",
                payment_method_types=["card"],
                line_items=[{"price": price_id, "quantity": 1}],
                customer_email=user_email,
                client_reference_id=user_id,
                metadata={
                    "user_id": user_id,
                    "tier": tier.value,
                },
                success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=cancel_url,
                allow_promotion_codes=True,
            )
            logger.info(f"[Stripe] Checkout session created for user {user_id}, tier={tier}")
            return session.url
        except Exception as e:
            logger.error(f"[Stripe] Failed to create checkout session: {e}")
            return None

    async def handle_webhook_event(self, event: dict) -> bool:
        """Process a Stripe webhook event"""
        event_type = event.get("type", "")
        event_id = event.get("id", "")

        logger.info(f"[Stripe Webhook] Processing {event_type} (id={event_id})")

        # Test event detection
        if event_id.startswith("evt_test_"):
            logger.info("[Stripe Webhook] Test event detected")
            return True

        handlers = {
            "checkout.session.completed": self._handle_checkout_completed,
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
            "invoice.paid": self._handle_invoice_paid,
        }

        handler = handlers.get(event_type)
        if handler:
            try:
                await handler(event)
                return True
            except Exception as e:
                logger.error(f"[Stripe Webhook] Error handling {event_type}: {e}")
                return False
        else:
            logger.info(f"[Stripe Webhook] Unhandled event type: {event_type}")
            return True

    async def _handle_checkout_completed(self, event: dict):
        """Handle successful checkout - activate subscription"""
        session = event["data"]["object"]
        user_id = session.get("client_reference_id") or session.get("metadata", {}).get("user_id")
        tier_str = session.get("metadata", {}).get("tier", "pro")
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")

        if not user_id:
            logger.error("[Stripe] No user_id in checkout session")
            return

        tier = SubscriptionTier(tier_str)
        credit_service = get_credit_service()
        await credit_service.set_tier(
            user_id=user_id,
            tier=tier,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
        )
        logger.info(f"[Stripe] User {user_id} subscribed to {tier}")

    async def _handle_subscription_updated(self, event: dict):
        """Handle subscription changes (upgrade/downgrade)"""
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer")
        status = subscription.get("status")

        if status == "active":
            # Find user by customer_id and update
            logger.info(f"[Stripe] Subscription updated for customer {customer_id}, status={status}")
        elif status in ("past_due", "unpaid"):
            logger.warning(f"[Stripe] Subscription {status} for customer {customer_id}")

    async def _handle_subscription_deleted(self, event: dict):
        """Handle subscription cancellation - downgrade to free"""
        subscription = event["data"]["object"]
        metadata = subscription.get("metadata", {})
        user_id = metadata.get("user_id")

        if user_id:
            credit_service = get_credit_service()
            await credit_service.set_tier(user_id, SubscriptionTier.FREE)
            logger.info(f"[Stripe] User {user_id} downgraded to free (subscription cancelled)")

    async def _handle_invoice_paid(self, event: dict):
        """Handle recurring invoice payment - refresh monthly credits"""
        invoice = event["data"]["object"]
        customer_id = invoice.get("customer")
        # Monthly credit refresh is handled by CreditService._check_monthly_reset
        logger.info(f"[Stripe] Invoice paid for customer {customer_id}")

    async def _ensure_price(self, tier: SubscriptionTier) -> Optional[str]:
        """Get or create a Stripe price for a tier"""
        if tier.value in self._price_cache:
            return self._price_cache[tier.value]

        stripe = _get_stripe()
        if not stripe:
            return None

        tier_config = TIERS[tier]
        product_key = f"{tier.value}_monthly"
        product_info = PRODUCTS.get(product_key)

        if not product_info:
            logger.error(f"[Stripe] No product definition for {product_key}")
            return None

        try:
            # Search for existing product
            products = stripe.Product.search(
                query=f"metadata['tier']:'{tier.value}'"
            )

            if products.data:
                product = products.data[0]
                # Get active price
                prices = stripe.Price.list(product=product.id, active=True, limit=1)
                if prices.data:
                    price_id = prices.data[0].id
                    self._price_cache[tier.value] = price_id
                    return price_id

            # Create new product + price
            product = stripe.Product.create(
                name=product_info["name"],
                description=product_info["description"],
                metadata={"tier": tier.value},
            )

            price = stripe.Price.create(
                product=product.id,
                unit_amount=tier_config.price_monthly_cents,
                currency="usd",
                recurring={"interval": "month"},
                metadata={"tier": tier.value},
            )

            self._price_cache[tier.value] = price.id
            logger.info(f"[Stripe] Created product+price for {tier.value}: {price.id}")
            return price.id

        except Exception as e:
            logger.error(f"[Stripe] Failed to ensure price for {tier.value}: {e}")
            return None

    async def get_customer_portal_url(
        self, stripe_customer_id: str, return_url: str
    ) -> Optional[str]:
        """Create a Stripe Customer Portal session for managing subscription"""
        stripe = _get_stripe()
        if not stripe or not stripe_customer_id:
            return None

        try:
            session = stripe.billing_portal.Session.create(
                customer=stripe_customer_id,
                return_url=return_url,
            )
            return session.url
        except Exception as e:
            logger.error(f"[Stripe] Failed to create portal session: {e}")
            return None


# Singleton
_stripe_service: Optional[StripeService] = None


def get_stripe_service() -> StripeService:
    global _stripe_service
    if _stripe_service is None:
        _stripe_service = StripeService()
    return _stripe_service
