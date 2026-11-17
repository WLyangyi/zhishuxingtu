<template>
  <section class="flat-panel">
    <header v-if="title || $slots.actions" class="flat-panel__header">
      <div class="flat-panel__heading">
        <span v-if="kicker" class="readout">{{ kicker }}</span>
        <h3 v-if="title" class="flat-panel__title">{{ title }}</h3>
      </div>
      <div v-if="$slots.actions" class="flat-panel__actions"><slot name="actions" /></div>
    </header>
    <div class="flat-panel__body"><slot /></div>
  </section>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ title?: string; kicker?: string }>(), { title: '', kicker: '' })
</script>

<style scoped>
.flat-panel {
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  background: var(--panel);
}

.flat-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--line);
}

.flat-panel__heading {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.flat-panel__title {
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.flat-panel__actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.flat-panel__body {
  padding: 16px;
}
</style>
