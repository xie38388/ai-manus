<template>
  <SimpleBar>
    <div class="flex flex-col items-center min-h-full w-full px-4 py-12">
      <!-- Header -->
      <div class="text-center mb-10">
        <h1 class="text-3xl font-bold text-[var(--text-primary)] mb-3">Choose Your Plan</h1>
        <p class="text-[var(--text-secondary)] text-base max-w-lg mx-auto">
          Start free, upgrade when you need more power. All plans include SOVR trust verification.
        </p>
      </div>

      <!-- Pricing Cards -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl w-full">
        <!-- Free -->
        <div class="flex flex-col rounded-2xl border border-[var(--border-main)] bg-[var(--background-main)] p-6 relative">
          <div class="mb-6">
            <h3 class="text-lg font-semibold text-[var(--text-primary)]">Free</h3>
            <div class="mt-3 flex items-baseline gap-1">
              <span class="text-4xl font-bold text-[var(--text-primary)]">$0</span>
              <span class="text-sm text-[var(--text-tertiary)]">/month</span>
            </div>
            <p class="mt-2 text-sm text-[var(--text-secondary)]">Try it out, no credit card needed</p>
          </div>
          <ul class="flex flex-col gap-3 mb-8 flex-1">
            <li class="flex items-start gap-2 text-sm text-[var(--text-secondary)]">
              <Check class="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
              <span>50 credits/month</span>
            </li>
            <li class="flex items-start gap-2 text-sm text-[var(--text-secondary)]">
              <Check class="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
              <span>5 agent tasks/day</span>
            </li>
            <li class="flex items-start gap-2 text-sm text-[var(--text-secondary)]">
              <Check class="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
              <span>1 concurrent agent</span>
            </li>
            <li class="flex items-start gap-2 text-sm text-[var(--text-secondary)]">
              <Check class="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
              <span>SOVR trust verification</span>
            </li>
          </ul>
          <button
            v-if="tier === 'free'"
            disabled
            class="w-full py-2.5 rounded-lg text-sm font-medium bg-[var(--fill-tsp-gray-main)] text-[var(--text-tertiary)] cursor-not-allowed"
          >
            Current Plan
          </button>
          <button
            v-else
            disabled
            class="w-full py-2.5 rounded-lg text-sm font-medium bg-[var(--fill-tsp-gray-main)] text-[var(--text-tertiary)] cursor-not-allowed"
          >
            Downgrade via Portal
          </button>
        </div>

        <!-- Pro (Recommended) -->
        <div class="flex flex-col rounded-2xl border-2 border-blue-500 bg-[var(--background-main)] p-6 relative shadow-lg">
          <div class="absolute -top-3 left-1/2 -translate-x-1/2 bg-blue-500 text-white text-xs font-semibold px-3 py-1 rounded-full">
            Most Popular
          </div>
          <div class="mb-6">
            <h3 class="text-lg font-semibold text-[var(--text-primary)]">Pro</h3>
            <div class="mt-3 flex items-baseline gap-1">
              <span class="text-4xl font-bold text-[var(--text-primary)]">$19.9</span>
              <span class="text-sm text-[var(--text-tertiary)]">/month</span>
            </div>
            <p class="mt-2 text-sm text-[var(--text-secondary)]">For serious users who need real power</p>
          </div>
          <ul class="flex flex-col gap-3 mb-8 flex-1">
            <li class="flex items-start gap-2 text-sm text-[var(--text-secondary)]">
              <Check class="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
              <span><strong>2,000</strong> credits/month</span>
            </li>
            <li class="flex items-start gap-2 text-sm text-[var(--text-secondary)]">
              <Check class="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
              <span><strong>100</strong> agent tasks/day</span>
            </li>
            <li class="flex items-start gap-2 text-sm text-[var(--text-secondary)]">
              <Check class="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
              <span><strong>3</strong> concurrent agents</span>
            </li>
            <li class="flex items-start gap-2 text-sm text-[var(--text-secondary)]">
              <Check class="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
              <span>SOVR trust verification</span>
            </li>
            <li class="flex items-start gap-2 text-sm text-[var(--text-secondary)]">
              <Check class="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
              <span>Priority support</span>
            </li>
          </ul>
          <button
            v-if="tier === 'pro'"
            @click="openPortal"
            class="w-full py-2.5 rounded-lg text-sm font-medium bg-blue-500/10 text-blue-500 hover:bg-blue-500/20 transition-colors cursor-pointer"
          >
            Manage Subscription
          </button>
          <button
            v-else
            @click="openCheckout('pro')"
            class="w-full py-2.5 rounded-lg text-sm font-medium bg-blue-500 text-white hover:bg-blue-600 transition-colors cursor-pointer"
          >
            Upgrade to Pro
          </button>
        </div>

        <!-- Team -->
        <div class="flex flex-col rounded-2xl border border-[var(--border-main)] bg-[var(--background-main)] p-6 relative">
          <div class="mb-6">
            <h3 class="text-lg font-semibold text-[var(--text-primary)]">Team</h3>
            <div class="mt-3 flex items-baseline gap-1">
              <span class="text-4xl font-bold text-[var(--text-primary)]">$49.9</span>
              <span class="text-sm text-[var(--text-tertiary)]">/seat/month</span>
            </div>
            <p class="mt-2 text-sm text-[var(--text-secondary)]">For teams that need unlimited power + audit</p>
          </div>
          <ul class="flex flex-col gap-3 mb-8 flex-1">
            <li class="flex items-start gap-2 text-sm text-[var(--text-secondary)]">
              <Check class="w-4 h-4 text-purple-500 mt-0.5 flex-shrink-0" />
              <span><strong>10,000</strong> credits/month</span>
            </li>
            <li class="flex items-start gap-2 text-sm text-[var(--text-secondary)]">
              <Check class="w-4 h-4 text-purple-500 mt-0.5 flex-shrink-0" />
              <span><strong>Unlimited</strong> agent tasks/day</span>
            </li>
            <li class="flex items-start gap-2 text-sm text-[var(--text-secondary)]">
              <Check class="w-4 h-4 text-purple-500 mt-0.5 flex-shrink-0" />
              <span><strong>10</strong> concurrent agents</span>
            </li>
            <li class="flex items-start gap-2 text-sm text-[var(--text-secondary)]">
              <Check class="w-4 h-4 text-purple-500 mt-0.5 flex-shrink-0" />
              <span>SOVR trust verification + audit export</span>
            </li>
            <li class="flex items-start gap-2 text-sm text-[var(--text-secondary)]">
              <Check class="w-4 h-4 text-purple-500 mt-0.5 flex-shrink-0" />
              <span>Team collaboration</span>
            </li>
            <li class="flex items-start gap-2 text-sm text-[var(--text-secondary)]">
              <Check class="w-4 h-4 text-purple-500 mt-0.5 flex-shrink-0" />
              <span>Dedicated support</span>
            </li>
          </ul>
          <button
            v-if="tier === 'team'"
            @click="openPortal"
            class="w-full py-2.5 rounded-lg text-sm font-medium bg-purple-500/10 text-purple-500 hover:bg-purple-500/20 transition-colors cursor-pointer"
          >
            Manage Subscription
          </button>
          <button
            v-else
            @click="openCheckout('team')"
            class="w-full py-2.5 rounded-lg text-sm font-medium border border-purple-500 text-purple-500 hover:bg-purple-500/10 transition-colors cursor-pointer"
          >
            Upgrade to Team
          </button>
        </div>
      </div>

      <!-- Credit Costs Info -->
      <div class="mt-12 max-w-2xl w-full">
        <h2 class="text-lg font-semibold text-[var(--text-primary)] mb-4 text-center">Credit Usage</h2>
        <div class="grid grid-cols-3 gap-4">
          <div class="flex flex-col items-center p-4 rounded-xl bg-[var(--fill-tsp-gray-main)]">
            <Bot class="w-6 h-6 text-blue-500 mb-2" />
            <span class="text-2xl font-bold text-[var(--text-primary)]">10</span>
            <span class="text-xs text-[var(--text-tertiary)]">credits / agent task</span>
          </div>
          <div class="flex flex-col items-center p-4 rounded-xl bg-[var(--fill-tsp-gray-main)]">
            <MessageSquare class="w-6 h-6 text-green-500 mb-2" />
            <span class="text-2xl font-bold text-[var(--text-primary)]">1</span>
            <span class="text-xs text-[var(--text-tertiary)]">credit / chat message</span>
          </div>
          <div class="flex flex-col items-center p-4 rounded-xl bg-[var(--fill-tsp-gray-main)]">
            <Image class="w-6 h-6 text-orange-500 mb-2" />
            <span class="text-2xl font-bold text-[var(--text-primary)]">5</span>
            <span class="text-xs text-[var(--text-tertiary)]">credits / image gen</span>
          </div>
        </div>
      </div>

      <!-- Back to Chat -->
      <div class="mt-8">
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
import { onMounted } from 'vue';
import { Check, Bot, MessageSquare, Image } from 'lucide-vue-next';
import SimpleBar from '../components/SimpleBar.vue';
import { useBilling } from '../composables/useBilling';

const { tier, openCheckout, openPortal, fetchBalance } = useBilling();

onMounted(() => {
  fetchBalance(true);
});
</script>
