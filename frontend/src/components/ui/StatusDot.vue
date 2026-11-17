<template>
  <span
    class="status-dot"
    :class="[toneClass, `status-dot--${size}`]"
    :role="label ? 'img' : undefined"
    :aria-label="label || undefined"
  >
    <span v-if="status === 'running'" class="status-dot__pulse" />
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type Status = 'idle' | 'running' | 'success' | 'warning' | 'error'

const props = withDefaults(
  defineProps<{ status?: Status; size?: 'sm' | 'md' | 'lg'; label?: string }>(),
  { status: 'idle', size: 'md' }
)

const toneClass = computed(
  () =>
    ({
      idle: 'bg-t3',
      running: 'bg-gold',
      success: 'bg-success',
      warning: 'bg-gold',
      error: 'bg-danger'
    })[props.status]
)
</script>

<style scoped>
.status-dot {
  position: relative;
  display: inline-flex;
  border-radius: 50%;
  flex: none;
}

.status-dot--sm { width: 4px; height: 4px; }
.status-dot--md { width: 6px; height: 6px; }
.status-dot--lg { width: 8px; height: 8px; }

.status-dot__pulse {
  position: absolute;
  inset: -3px;
  border-radius: 50%;
  border: 1px solid var(--gold);
  opacity: 0;
  animation: dot-pulse 2.4s var(--ease-out) infinite;
}

@keyframes dot-pulse {
  0% { transform: scale(0.6); opacity: 0.7; }
  70% { transform: scale(1.4); opacity: 0; }
  100% { transform: scale(1.4); opacity: 0; }
}
</style>
