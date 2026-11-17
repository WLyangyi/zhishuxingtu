<template>
  <component :is="as" :class="classes">
    <header v-if="title || $slots.header || $slots.actions" class="card__header">
      <div class="card__heading">
        <slot name="header">
          <h3 v-if="title" class="card__title">{{ title }}</h3>
          <p v-if="description" class="card__description">{{ description }}</p>
        </slot>
      </div>
      <div v-if="$slots.actions" class="card__actions"><slot name="actions" /></div>
    </header>

    <div class="card__body"><slot /></div>

    <footer v-if="$slots.footer" class="card__footer"><slot name="footer" /></footer>
  </component>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/cn'

const props = withDefaults(
  defineProps<{
    as?: string
    title?: string
    description?: string
    padding?: 'none' | 'sm' | 'md' | 'lg'
    interactive?: boolean
    flat?: boolean
  }>(),
  { as: 'div', title: '', description: '', padding: 'md', interactive: false, flat: false }
)

const paddings = { none: '', sm: 'p-3', md: 'p-5', lg: 'p-7' }

const classes = computed(() =>
  cn(
    'rounded-lg border border-line',
    props.flat ? 'bg-transparent' : 'bg-panel',
    paddings[props.padding],
    props.interactive &&
      'transition-colors duration-base ease-out hover:border-line-strong hover:bg-panel-2 cursor-pointer'
  )
)
</script>

<style scoped>
.card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.card__title {
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: var(--text);
}

.card__description {
  margin-top: 4px;
  font-size: 12px;
  color: var(--t2);
}

.card__actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: none;
}

.card__footer {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--line);
}
</style>
