<template>
  <header class="page-header">
    <div class="page-header__main">
      <span v-if="kicker" class="readout">{{ kicker }}</span>
      <div class="page-header__title-row">
        <h1 class="page-header__title">{{ title }}</h1>
        <slot name="badge" />
      </div>
      <p v-if="description" class="page-header__description">{{ description }}</p>
      <slot name="meta" />
    </div>
    <div v-if="$slots.actions" class="page-header__actions"><slot name="actions" /></div>
  </header>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ title: string; kicker?: string; description?: string }>(), {
  kicker: '',
  description: ''
})
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--line);
}

.page-header__main {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.page-header__title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.page-header__title {
  font-family: var(--font-display);
  font-size: var(--fs-d2);
  font-weight: 500;
  letter-spacing: -0.03em;
  line-height: 1.1;
  color: var(--text);
}

.page-header__description {
  max-width: 640px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--t2);
}

.page-header__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: none;
  padding-bottom: 2px;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .page-header__title {
    font-size: 30px;
  }
}
</style>
