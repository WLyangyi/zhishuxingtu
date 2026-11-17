<template>
  <div class="empty-state">
    <svg class="empty-state__art" viewBox="0 0 120 64" aria-hidden="true">
      <path d="M18 46 L46 22 L74 40 L102 16" class="empty-state__line" />
      <circle cx="18" cy="46" r="2" class="empty-state__star" />
      <circle cx="46" cy="22" r="2.4" class="empty-state__star empty-state__star--gold" />
      <circle cx="74" cy="40" r="1.8" class="empty-state__star" />
      <circle cx="102" cy="16" r="2.2" class="empty-state__star" />
    </svg>

    <h3 class="empty-state__title">{{ title }}</h3>
    <p v-if="description" class="empty-state__description">{{ description }}</p>
    <div v-if="$slots.default" class="empty-state__action"><slot /></div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ title?: string; description?: string }>(), {
  title: '这里还没有内容',
  description: ''
})
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 48px 24px;
  text-align: center;
}

.empty-state__art {
  width: 120px;
  height: 64px;
  margin-bottom: 8px;
  opacity: 0.8;
}

.empty-state__line {
  fill: none;
  stroke: var(--line-strong);
  stroke-width: 1;
}

.empty-state__star {
  fill: var(--t3);
}

.empty-state__star--gold {
  fill: var(--gold);
}

.empty-state__title {
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 500;
  letter-spacing: -0.01em;
  color: var(--t2);
}

.empty-state__description {
  max-width: 320px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--t3);
}

.empty-state__action {
  margin-top: 10px;
}
</style>
