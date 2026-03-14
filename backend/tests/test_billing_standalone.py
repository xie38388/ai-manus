"""
Standalone Billing tests - no langchain/beanie dependency needed.
Tests Credit Service and Products module directly.
"""
import sys
import os
import types
import importlib
import importlib.util

# Setup path
backend_dir = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, backend_dir)

# Create stub packages to avoid triggering __init__.py imports
for pkg in [
    'app', 'app.domain', 'app.domain.services', 'app.domain.services.billing',
    'app.core',
]:
    if pkg not in sys.modules:
        mod = types.ModuleType(pkg)
        mod.__path__ = [os.path.join(backend_dir, pkg.replace('.', '/'))]
        mod.__package__ = pkg
        sys.modules[pkg] = mod

# Mock config module
config_mod = types.ModuleType('app.core.config')
class MockSettings:
    stripe_secret_key = None
    stripe_publishable_key = None
    stripe_webhook_secret = None
config_mod.get_settings = lambda: MockSettings()
sys.modules['app.core.config'] = config_mod

# Import modules directly
def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

products_mod = _load_module(
    "app.domain.services.billing.products",
    os.path.join(backend_dir, "app/domain/services/billing/products.py"))

credit_mod = _load_module(
    "app.domain.services.billing.credit_service",
    os.path.join(backend_dir, "app/domain/services/billing/credit_service.py"))

SubscriptionTier = products_mod.SubscriptionTier
TIERS = products_mod.TIERS
CREDIT_COSTS = products_mod.CREDIT_COSTS
CreditService = credit_mod.CreditService

import asyncio

def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ── Product Tests ────────────────────────────────────────────────────

def test_tiers_defined():
    assert len(TIERS) == 3
    assert SubscriptionTier.FREE in TIERS
    assert SubscriptionTier.PRO in TIERS
    assert SubscriptionTier.TEAM in TIERS
    print("  ✅ 3 tiers defined (Free/Pro/Team)")

def test_free_tier_is_free():
    free = TIERS[SubscriptionTier.FREE]
    assert free.price_monthly_cents == 0
    assert free.daily_agent_limit == 5
    print(f"  ✅ Free tier: $0, {free.daily_agent_limit} agents/day, {free.credits_monthly} credits")

def test_pro_tier_pricing():
    pro = TIERS[SubscriptionTier.PRO]
    assert pro.price_monthly_cents == 1990
    assert pro.credits_monthly == 2000
    print(f"  ✅ Pro tier: ${pro.price_monthly_cents/100}/mo, {pro.credits_monthly} credits")

def test_team_tier_pricing():
    team = TIERS[SubscriptionTier.TEAM]
    assert team.price_monthly_cents == 4990
    assert team.daily_agent_limit == -1  # unlimited
    print(f"  ✅ Team tier: ${team.price_monthly_cents/100}/mo, unlimited agents")

def test_credit_costs():
    assert CREDIT_COSTS["agent_task"] == 10
    assert CREDIT_COSTS["chat_message"] == 1
    assert CREDIT_COSTS["image_generation"] == 5
    print(f"  ✅ Credit costs: agent={CREDIT_COSTS['agent_task']}, chat={CREDIT_COSTS['chat_message']}, image={CREDIT_COSTS['image_generation']}")


# ── Credit Service Tests ─────────────────────────────────────────────

def test_new_user_gets_free_credits():
    svc = CreditService()
    balance = run(svc.get_balance("user1"))
    assert balance.tier == SubscriptionTier.FREE
    assert balance.credits_remaining == TIERS[SubscriptionTier.FREE].credits_monthly
    print(f"  ✅ New user gets {balance.credits_remaining} free credits")

def test_credit_check_allows_chat():
    svc = CreditService()
    result = run(svc.check_credits("user2", "chat_message"))
    assert result.allowed is True
    assert result.credits_required == 1
    print(f"  ✅ Chat allowed: cost={result.credits_required}, remaining={result.credits_remaining}")

def test_credit_check_allows_agent():
    svc = CreditService()
    result = run(svc.check_credits("user3", "agent_task"))
    assert result.allowed is True
    assert result.credits_required == 10
    print(f"  ✅ Agent task allowed: cost={result.credits_required}")

def test_credit_consumption():
    svc = CreditService()
    balance_before = run(svc.get_balance("user4"))
    initial = balance_before.credits_remaining
    run(svc.consume_credits("user4", "agent_task"))
    balance_after = run(svc.get_balance("user4"))
    assert balance_after.credits_remaining == initial - 10
    assert balance_after.credits_used_today == 10
    assert balance_after.daily_agent_count == 1
    print(f"  ✅ Credits consumed: {initial} → {balance_after.credits_remaining}")

def test_daily_agent_limit():
    svc = CreditService()
    # Give enough credits
    run(svc.add_credits("user5", 1000))
    # Exhaust daily limit (5 for free)
    for i in range(5):
        run(svc.consume_credits("user5", "agent_task"))
    result = run(svc.check_credits("user5", "agent_task"))
    assert result.allowed is False
    assert "Daily agent task limit" in result.reason
    print(f"  ✅ Daily agent limit enforced: {result.reason}")

def test_insufficient_credits():
    svc = CreditService()
    # Drain all credits
    balance = run(svc.get_balance("user6"))
    run(svc.consume_credits("user6", "agent_task", balance.credits_remaining))
    result = run(svc.check_credits("user6", "agent_task"))
    assert result.allowed is False
    assert "Insufficient credits" in result.reason
    print(f"  ✅ Insufficient credits blocked: {result.reason}")

def test_tier_upgrade():
    svc = CreditService()
    balance_before = run(svc.get_balance("user7"))
    assert balance_before.tier == SubscriptionTier.FREE
    initial_credits = balance_before.credits_remaining

    run(svc.set_tier("user7", SubscriptionTier.PRO, "cus_123", "sub_456"))
    balance_after = run(svc.get_balance("user7"))
    assert balance_after.tier == SubscriptionTier.PRO
    assert balance_after.stripe_customer_id == "cus_123"
    assert balance_after.credits_remaining > initial_credits
    print(f"  ✅ Tier upgrade: FREE→PRO, credits {initial_credits}→{balance_after.credits_remaining}")

def test_tier_downgrade():
    svc = CreditService()
    run(svc.set_tier("user8", SubscriptionTier.PRO))
    run(svc.set_tier("user8", SubscriptionTier.FREE))
    balance = run(svc.get_balance("user8"))
    assert balance.tier == SubscriptionTier.FREE
    print(f"  ✅ Tier downgrade: PRO→FREE")

def test_add_credits():
    svc = CreditService()
    balance = run(svc.get_balance("user9"))
    initial = balance.credits_remaining
    run(svc.add_credits("user9", 500))
    balance = run(svc.get_balance("user9"))
    assert balance.credits_remaining == initial + 500
    print(f"  ✅ Add credits: {initial} + 500 = {balance.credits_remaining}")

def test_usage_stats():
    svc = CreditService()
    run(svc.consume_credits("user10", "agent_task"))
    run(svc.consume_credits("user10", "chat_message"))
    stats = run(svc.get_usage_stats("user10"))
    assert stats["tier"] == "free"
    assert stats["credits_used_today"] == 11
    assert stats["daily_agent_count"] == 1
    assert "usage_percent" in stats
    print(f"  ✅ Usage stats: used_today={stats['credits_used_today']}, usage={stats['usage_percent']}%")

def test_pro_higher_limits():
    svc = CreditService()
    run(svc.set_tier("user11", SubscriptionTier.PRO))
    # Pro has 100 daily agent limit
    for i in range(10):
        result = run(svc.check_credits("user11", "agent_task"))
        assert result.allowed is True
        run(svc.consume_credits("user11", "agent_task"))
    print(f"  ✅ Pro tier: 10 agent tasks allowed (limit=100)")

def test_team_unlimited_agents():
    svc = CreditService()
    run(svc.set_tier("user12", SubscriptionTier.TEAM))
    result = run(svc.check_credits("user12", "agent_task"))
    assert result.allowed is True
    assert result.daily_agent_remaining == -1  # unlimited
    print(f"  ✅ Team tier: unlimited agents (daily_remaining={result.daily_agent_remaining})")


if __name__ == "__main__":
    tests = [
        ("Products & Pricing", [
            test_tiers_defined, test_free_tier_is_free,
            test_pro_tier_pricing, test_team_tier_pricing, test_credit_costs,
        ]),
        ("Credit Service", [
            test_new_user_gets_free_credits, test_credit_check_allows_chat,
            test_credit_check_allows_agent, test_credit_consumption,
            test_daily_agent_limit, test_insufficient_credits,
            test_tier_upgrade, test_tier_downgrade, test_add_credits,
            test_usage_stats, test_pro_higher_limits, test_team_unlimited_agents,
        ]),
    ]

    total = passed = failed = 0
    for group_name, group_tests in tests:
        print(f"\n{'='*50}")
        print(f"  {group_name}")
        print(f"{'='*50}")
        for test_fn in group_tests:
            total += 1
            try:
                test_fn()
                passed += 1
            except Exception as e:
                failed += 1
                print(f"  ❌ {test_fn.__name__}: {e}")
                import traceback
                traceback.print_exc()

    print(f"\n{'='*50}")
    print(f"  Results: {passed}/{total} passed, {failed} failed")
    print(f"{'='*50}")
    sys.exit(1 if failed else 0)
