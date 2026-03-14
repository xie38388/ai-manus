<template>
  <div class="px-3 pb-3">
    <div
      @click="handleClick"
      class="flex items-center gap-2 px-3 py-2.5 rounded-xl cursor-pointer transition-colors"
      :class="isLowCredits
        ? 'bg-red-500/10 hover:bg-red-500/15'
        : 'bg-[var(--fill-tsp-gray-main)] hover:bg-[var(--fill-tsp-gray-main-hover)]'"
    >
      <!-- Credit icon -->
      <div class="flex items-center justify-center w-8 h-8 rounded-lg flex-shrink-0"
        :class="isLowCredits ? 'bg-red-500/20' : 'bg-blue-500/20'">
        <Zap class="w-4 h-4" :class="isLowCredits ? 'text-red-500' : 'text-blue-500'" />
      </div>

      <!-- Info -->
      <div class="flex flex-col flex-1 min-w-0">
        <div class="flex items-center justify-between">
          <span class="text-xs font-medium text-[var(--text-primary)] truncate">
            {{ creditsRemaining }} credits
          </span>
          <span class="text-xs px-1.5 py-0.5 rounded-md font-medium"
            :class="tierBadgeClass">
            {{ tierName }}
          </span>
        </div>
        <!-- Progress bar -->
        <div class="mt-1.5 h-1.5 rounded-full bg-[var(--border-light)] overflow-hidden">
          <div
            class="h-full rounded-full transition-all duration-500"
            :class="isLowCredits ? 'bg-red-500' : 'bg-blue-500'"
            :style="{ width: `${creditsPercent}%` }"
          />
        </div>
      </div>
    </div>

    <!-- Low credits warning -->
    <div v-if="isLowCredits && isFree" class="mt-1.5 px-1">
      <button
        @click="$router.push('/pricing')"
        class="w-full text-xs text-center py-1.5 rounded-lg bg-blue-500 text-white hover:bg-blue-600 transition-colors cursor-pointer"
      >
        Upgrade for more credits →
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { Zap } from 'lucide-vue-next';
import { useBilling } from '../composables/useBilling';

const router = useRouter();
const {
  tierName, creditsRemaining, creditsPercent,
  isLowCredits, isFree, tier,
  fetchBalance,
} = useBilling();

const tierBadgeClass = computed(() => {
  switch (tier.value) {
    case 'pro': return 'bg-blue-500/10 text-blue-500';
    case 'team': return 'bg-purple-500/10 text-purple-500';
    default: return 'bg-[var(--fill-tsp-gray-main)] text-[var(--text-tertiary)]';
  }
});

function handleClick() {
  router.push('/pricing');
}

onMounted(() => {
  fetchBalance();
});
</script>
