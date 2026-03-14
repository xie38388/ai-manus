<template>
  <SimpleBar>
    <div class="flex flex-col w-full max-w-3xl mx-auto px-4 py-8">
      <!-- Header -->
      <div class="mb-8">
        <h1 class="text-2xl font-bold text-[var(--text-primary)]">Usage Dashboard</h1>
        <p class="text-sm text-[var(--text-secondary)] mt-1">Monitor your credit usage and subscription status</p>
      </div>

      <!-- Subscription Card -->
      <div class="rounded-2xl border border-[var(--border-main)] bg-[var(--background-main)] p-6 mb-6">
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl flex items-center justify-center"
              :class="tierBgClass">
              <Crown class="w-5 h-5" :class="tierIconClass" />
            </div>
            <div>
              <h2 class="text-lg font-semibold text-[var(--text-primary)]">{{ tierName }} Plan</h2>
              <p class="text-xs text-[var(--text-tertiary)]">Current billing period</p>
            </div>
          </div>
          <button
            v-if="!isFree"
            @click="openPortal"
            class="text-sm px-4 py-2 rounded-lg border border-[var(--border-main)] text-[var(--text-secondary)] hover:bg-[var(--fill-tsp-gray-main)] transition-colors cursor-pointer"
          >
            Manage Subscription
          </button>
          <button
            v-else
            @click="$router.push('/pricing')"
            class="text-sm px-4 py-2 rounded-lg bg-blue-500 text-white hover:bg-blue-600 transition-colors cursor-pointer"
          >
            Upgrade
          </button>
        </div>

        <!-- Credits Overview -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="p-4 rounded-xl bg-[var(--fill-tsp-gray-main)]">
            <p class="text-xs text-[var(--text-tertiary)] mb-1">Credits Remaining</p>
            <p class="text-2xl font-bold text-[var(--text-primary)]">{{ creditsRemaining }}</p>
            <p class="text-xs text-[var(--text-tertiary)]">of {{ creditsTotal }}</p>
          </div>
          <div class="p-4 rounded-xl bg-[var(--fill-tsp-gray-main)]">
            <p class="text-xs text-[var(--text-tertiary)] mb-1">Used Today</p>
            <p class="text-2xl font-bold text-[var(--text-primary)]">{{ balance?.credits_used_today ?? 0 }}</p>
            <p class="text-xs text-[var(--text-tertiary)]">credits</p>
          </div>
          <div class="p-4 rounded-xl bg-[var(--fill-tsp-gray-main)]">
            <p class="text-xs text-[var(--text-tertiary)] mb-1">Agent Tasks Today</p>
            <p class="text-2xl font-bold text-[var(--text-primary)]">{{ dailyAgentCount }}</p>
            <p class="text-xs text-[var(--text-tertiary)]">
              of {{ dailyAgentLimit === -1 ? '∞' : dailyAgentLimit }}
            </p>
          </div>
          <div class="p-4 rounded-xl bg-[var(--fill-tsp-gray-main)]">
            <p class="text-xs text-[var(--text-tertiary)] mb-1">Used This Month</p>
            <p class="text-2xl font-bold text-[var(--text-primary)]">{{ balance?.credits_used_month ?? 0 }}</p>
            <p class="text-xs text-[var(--text-tertiary)]">credits</p>
          </div>
        </div>

        <!-- Progress Bar -->
        <div class="mt-4">
          <div class="flex justify-between text-xs text-[var(--text-tertiary)] mb-1.5">
            <span>Credit Usage</span>
            <span>{{ 100 - creditsPercent }}% used</span>
          </div>
          <div class="h-2 rounded-full bg-[var(--border-light)] overflow-hidden">
            <div
              class="h-full rounded-full transition-all duration-700"
              :class="progressBarClass"
              :style="{ width: `${creditsPercent}%` }"
            />
          </div>
        </div>

        <!-- Prediction -->
        <div v-if="daysUntilExhausted !== null" class="mt-4 px-4 py-3 rounded-xl" :class="predictionBgClass">
          <div class="flex items-center gap-2">
            <TrendingDown v-if="daysUntilExhausted <= 7" class="w-4 h-4 text-orange-500" />
            <TrendingUp v-else class="w-4 h-4 text-green-500" />
            <span class="text-sm" :class="predictionTextClass">
              <template v-if="daysUntilExhausted <= 0">
                Credits exhausted. Upgrade for more.
              </template>
              <template v-else-if="daysUntilExhausted <= 7">
                At current pace, credits will run out in ~{{ daysUntilExhausted }} days.
              </template>
              <template v-else>
                Credits looking healthy. ~{{ daysUntilExhausted }} days remaining at current pace.
              </template>
            </span>
          </div>
        </div>
      </div>

      <!-- SOVR Trust Score -->
      <div class="rounded-2xl border border-[var(--border-main)] bg-[var(--background-main)] p-6 mb-6">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-10 h-10 rounded-xl bg-green-500/10 flex items-center justify-center">
            <ShieldCheck class="w-5 h-5 text-green-500" />
          </div>
          <div>
            <h2 class="text-lg font-semibold text-[var(--text-primary)]">SOVR Trust Score</h2>
            <p class="text-xs text-[var(--text-tertiary)]">AI safety verification powered by SOVR</p>
          </div>
        </div>
        <div class="grid grid-cols-3 gap-4">
          <div class="p-4 rounded-xl bg-[var(--fill-tsp-gray-main)] text-center">
            <p class="text-3xl font-bold text-green-500">{{ sovrStats.trust_score ?? 100 }}</p>
            <p class="text-xs text-[var(--text-tertiary)] mt-1">Trust Score</p>
          </div>
          <div class="p-4 rounded-xl bg-[var(--fill-tsp-gray-main)] text-center">
            <p class="text-3xl font-bold text-[var(--text-primary)]">{{ sovrStats.total_checks ?? 0 }}</p>
            <p class="text-xs text-[var(--text-tertiary)] mt-1">Total Checks</p>
          </div>
          <div class="p-4 rounded-xl bg-[var(--fill-tsp-gray-main)] text-center">
            <p class="text-3xl font-bold text-red-500">{{ sovrStats.blocked_count ?? 0 }}</p>
            <p class="text-xs text-[var(--text-tertiary)] mt-1">Blocked Actions</p>
          </div>
        </div>
      </div>

      <!-- Credit Cost Reference -->
      <div class="rounded-2xl border border-[var(--border-main)] bg-[var(--background-main)] p-6">
        <h2 class="text-lg font-semibold text-[var(--text-primary)] mb-4">Credit Costs</h2>
        <div class="space-y-3">
          <div class="flex items-center justify-between py-2 border-b border-[var(--border-light)]">
            <div class="flex items-center gap-2">
              <Bot class="w-4 h-4 text-blue-500" />
              <span class="text-sm text-[var(--text-secondary)]">Agent Task</span>
            </div>
            <span class="text-sm font-semibold text-[var(--text-primary)]">10 credits</span>
          </div>
          <div class="flex items-center justify-between py-2 border-b border-[var(--border-light)]">
            <div class="flex items-center gap-2">
              <MessageSquare class="w-4 h-4 text-green-500" />
              <span class="text-sm text-[var(--text-secondary)]">Chat Message</span>
            </div>
            <span class="text-sm font-semibold text-[var(--text-primary)]">1 credit</span>
          </div>
          <div class="flex items-center justify-between py-2">
            <div class="flex items-center gap-2">
              <ImageIcon class="w-4 h-4 text-orange-500" />
              <span class="text-sm text-[var(--text-secondary)]">Image Generation</span>
            </div>
            <span class="text-sm font-semibold text-[var(--text-primary)]">5 credits</span>
          </div>
        </div>
      </div>

      <!-- Back -->
      <div class="mt-6 text-center">
        <button
          @click="$router.push('/chat')"
          class="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
        >
          ← Back to Chat
        </button>
      </div>
    </div>
  </SimpleBar>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { Crown, ShieldCheck, Bot, MessageSquare, Image as ImageIcon, TrendingDown, TrendingUp } from 'lucide-vue-next';
import SimpleBar from '../components/SimpleBar.vue';
import { useBilling } from '../composables/useBilling';
import { apiClient, ApiResponse } from '../api/client';

const {
  balance, tierName, creditsRemaining, creditsTotal, creditsPercent,
  isFree, tier, dailyAgentCount, dailyAgentLimit,
  fetchBalance, openPortal,
} = useBilling();

// SOVR stats
const sovrStats = ref<{ trust_score: number; total_checks: number; blocked_count: number }>({
  trust_score: 100,
  total_checks: 0,
  blocked_count: 0,
});

// Prediction: days until credits exhausted
const daysUntilExhausted = computed(() => {
  if (!balance.value) return null;
  const usedToday = balance.value.credits_used_today;
  if (usedToday <= 0) return null; // No usage today, can't predict
  const remaining = balance.value.credits_remaining;
  return Math.ceil(remaining / usedToday);
});

// Styling
const tierBgClass = computed(() => {
  switch (tier.value) {
    case 'pro': return 'bg-blue-500/10';
    case 'team': return 'bg-purple-500/10';
    default: return 'bg-[var(--fill-tsp-gray-main)]';
  }
});
const tierIconClass = computed(() => {
  switch (tier.value) {
    case 'pro': return 'text-blue-500';
    case 'team': return 'text-purple-500';
    default: return 'text-[var(--text-tertiary)]';
  }
});
const progressBarClass = computed(() => {
  if (creditsPercent.value <= 20) return 'bg-red-500';
  if (creditsPercent.value <= 50) return 'bg-orange-500';
  return 'bg-blue-500';
});
const predictionBgClass = computed(() => {
  if (!daysUntilExhausted.value || daysUntilExhausted.value <= 7) return 'bg-orange-500/10';
  return 'bg-green-500/10';
});
const predictionTextClass = computed(() => {
  if (!daysUntilExhausted.value || daysUntilExhausted.value <= 7) return 'text-orange-500';
  return 'text-green-500';
});

// Fetch SOVR stats
async function fetchSovrStats() {
  try {
    const response = await apiClient.get<ApiResponse<any>>('/sovr/stats');
    sovrStats.value = response.data.data;
  } catch (err: any) {
    console.warn('[SOVR] Failed to fetch stats:', err.message);
  }
}

onMounted(() => {
  fetchBalance(true);
  fetchSovrStats();
});
</script>
