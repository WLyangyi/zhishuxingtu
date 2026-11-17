<template>
  <div class="skeleton-stack" :aria-busy="true" aria-label="加载中">
    <span
      v-for="line in lineCount"
      :key="line"
      class="skeleton"
      :style="{
        width: line === lineCount && lineCount > 1 ? '62%' : typeof width === 'number' ? `${width}px` : width,
        height: typeof height === 'number' ? `${height}px` : height,
        borderRadius: rounded ? 'var(--r-md)' : 'var(--r-sm)'
      }"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    width?: string | number
    height?: string | number
    lines?: number
    rounded?: boolean
  }>(),
  { width: '100%', height: 12, lines: 1, rounded: false }
)

const lineCount = computed(() => Math.max(1, props.lines))
</script>

<style scoped>
.skeleton-stack {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.skeleton {
  display: block;
  background: linear-gradient(
    90deg,
    var(--panel) 25%,
    var(--panel-2) 50%,
    var(--panel) 75%
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.6s linear infinite;
}

@keyframes skeleton-shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
</style>
