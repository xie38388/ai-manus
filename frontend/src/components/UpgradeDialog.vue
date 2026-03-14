<template>
  <Teleport to="body">
    <div v-if="visible" class="fixed inset-0 z-[100] flex items-center justify-center">
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black/50" @click="close" />

      <!-- Dialog -->
      <div class="relative bg-[var(--background-main)] rounded-2xl shadow-2xl max-w-md w-full mx-4 p-6 z-10">
        <!-- Close -->
        <button @click="close"
          class="absolute top-4 right-4 text-[var(--text-tertiary)] hover:text-[var(--text-primary)] cursor-pointer">
          <X class="w-5 h-5" />
        </button>

        <!-- Icon -->
        <div class="flex justify-center mb-4">
          <div class="w-14 h-14 rounded-full bg-orange-500/10 flex items-center justify-center">
            <AlertTriangle class="w-7 h-7 text-orange-500" />
          </div>
        </div>

        <!-- Content -->
        <h3 class="text-lg font-semibold text-[var(--text-primary)] text-center mb-2">
          {{ title }}
        </h3>
        <p class="text-sm text-[var(--text-secondary)] text-center mb-6">
          {{ message }}
        </p>

        <!-- Current balance -->
        <div class="flex items-center justify-between px-4 py-3 rounded-xl bg-[var(--fill-tsp-gray-main)] mb-6">
          <span class="text-sm text-[var(--text-secondary)]">Credits remaining</span>
          <span class="text-sm font-semibold" :class="creditsRemaining <= 0 ? 'text-red-500' : 'text-[var(--text-primary)]'">
            {{ creditsRemaining }} / {{ creditsTotal }}
          </span>
        </div>

        <!-- Actions -->
        <div class="flex gap-3">
          <button @click="close"
            class="flex-1 py-2.5 rounded-lg text-sm font-medium border border-[var(--border-main)] text-[var(--text-secondary)] hover:bg-[var(--fill-tsp-gray-main)] transition-colors cursor-pointer">
            Later
          </button>
          <button @click="handleUpgrade"
            class="flex-1 py-2.5 rounded-lg text-sm font-medium bg-blue-500 text-white hover:bg-blue-600 transition-colors cursor-pointer">
            Upgrade Now
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { X, AlertTriangle } from 'lucide-vue-next';
import { useBilling } from '../composables/useBilling';

const props = withDefaults(defineProps<{
  visible: boolean;
  title?: string;
  message?: string;
}>(), {
  title: 'Credits Running Low',
  message: 'You need more credits to continue using this feature. Upgrade your plan for more credits and higher limits.',
});

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void;
}>();

const router = useRouter();
const { creditsRemaining, creditsTotal } = useBilling();

function close() {
  emit('update:visible', false);
}

function handleUpgrade() {
  close();
  router.push('/pricing');
}
</script>
