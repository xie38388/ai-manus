/**
 * Billing composable - Global credit balance and subscription state.
 */
import { ref, computed, readonly } from 'vue';
import { getBalance, getUsageStats, createCheckout, createPortal } from '../api/billing';
import type { CreditBalance, UsageStats } from '../api/billing';
import { showErrorToast, showSuccessToast } from '../utils/toast';

// ── Shared State (singleton) ─────────────────────────────────────────

const balance = ref<CreditBalance | null>(null);
const usage = ref<UsageStats | null>(null);
const isLoading = ref(false);
const lastFetched = ref(0);

const CACHE_TTL = 30_000; // 30 seconds

// ── Computed ─────────────────────────────────────────────────────────

const tier = computed(() => balance.value?.tier ?? 'free');
const tierName = computed(() => balance.value?.tier_name ?? 'Free');
const creditsRemaining = computed(() => balance.value?.credits_remaining ?? 0);
const creditsTotal = computed(() => balance.value?.credits_total ?? 50);
const creditsPercent = computed(() => {
  if (!creditsTotal.value) return 0;
  return Math.round((creditsRemaining.value / creditsTotal.value) * 100);
});
const isLowCredits = computed(() => creditsPercent.value <= 20);
const isFree = computed(() => tier.value === 'free');
const isPro = computed(() => tier.value === 'pro');
const isTeam = computed(() => tier.value === 'team');
const dailyAgentCount = computed(() => balance.value?.daily_agent_count ?? 0);
const dailyAgentLimit = computed(() => balance.value?.daily_agent_limit ?? 5);
const dailyAgentRemaining = computed(() => {
  if (dailyAgentLimit.value === -1) return -1; // unlimited
  return Math.max(0, dailyAgentLimit.value - dailyAgentCount.value);
});

// ── Actions ──────────────────────────────────────────────────────────

async function fetchBalance(force = false) {
  const now = Date.now();
  if (!force && balance.value && (now - lastFetched.value) < CACHE_TTL) {
    return; // Use cached
  }

  isLoading.value = true;
  try {
    balance.value = await getBalance();
    lastFetched.value = now;
  } catch (err: any) {
    // Billing not configured yet — use defaults silently
    console.warn('[Billing] Failed to fetch balance:', err.message);
  } finally {
    isLoading.value = false;
  }
}

async function fetchUsage() {
  try {
    usage.value = await getUsageStats();
  } catch (err: any) {
    console.warn('[Billing] Failed to fetch usage:', err.message);
  }
}

async function openCheckout(tierSlug: string) {
  try {
    const url = await createCheckout(
      tierSlug,
      `${window.location.origin}/chat?upgrade=success`,
      `${window.location.origin}/pricing?upgrade=cancelled`
    );
    window.open(url, '_blank');
    showSuccessToast('Redirecting to checkout...');
  } catch (err: any) {
    showErrorToast(err.message || 'Failed to create checkout session');
  }
}

async function openPortal() {
  try {
    const url = await createPortal(`${window.location.origin}/chat`);
    window.open(url, '_blank');
  } catch (err: any) {
    showErrorToast(err.message || 'Failed to open subscription portal');
  }
}

// ── Export ────────────────────────────────────────────────────────────

export function useBilling() {
  return {
    // State
    balance: readonly(balance),
    usage: readonly(usage),
    isLoading: readonly(isLoading),

    // Computed
    tier,
    tierName,
    creditsRemaining,
    creditsTotal,
    creditsPercent,
    isLowCredits,
    isFree,
    isPro,
    isTeam,
    dailyAgentCount,
    dailyAgentLimit,
    dailyAgentRemaining,

    // Actions
    fetchBalance,
    fetchUsage,
    openCheckout,
    openPortal,
  };
}
