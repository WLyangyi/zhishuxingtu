<template>
  <div ref="root" class="seg" role="radiogroup" :aria-label="ariaLabel">
    <button
      v-for="(item, index) in items"
      :key="item.value"
      type="button"
      role="radio"
      :aria-checked="item.value === modelValue"
      :tabindex="item.value === modelValue ? 0 : -1"
      :class="['seg__item', `seg__item--${size}`, item.value === modelValue && 'seg__item--active']"
      @click="select(item.value)"
      @keydown="onKeydown($event, index)"
    >
      {{ item.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { nextTick, ref } from 'vue'

export interface SegmentItem {
  label: string
  value: string
}

const props = withDefaults(
  defineProps<{
    items: SegmentItem[]
    modelValue?: string
    size?: 'sm' | 'md'
    ariaLabel?: string
  }>(),
  { modelValue: '', size: 'md', ariaLabel: '视图切换' }
)

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const root = ref<HTMLElement | null>(null)

function select(value: string) {
  if (value !== props.modelValue) emit('update:modelValue', value)
}

function onKeydown(event: KeyboardEvent, index: number) {
  const last = props.items.length - 1
  let next = index

  if (event.key === 'ArrowRight' || event.key === 'ArrowDown') next = index === last ? 0 : index + 1
  else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') next = index === 0 ? last : index - 1
  else if (event.key === 'Home') next = 0
  else if (event.key === 'End') next = last
  else return

  event.preventDefault()
  select(props.items[next].value)
  nextTick(() => {
    const buttons = root.value?.querySelectorAll<HTMLButtonElement>('button')
    buttons?.[next]?.focus()
  })
}
</script>

<style scoped>
.seg {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
}

.seg__item {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--r-sm);
  color: var(--t3);
  font-weight: 500;
  transition: color var(--d-fast) var(--ease-out),
    background-color var(--d-fast) var(--ease-out);
  white-space: nowrap;
}

.seg__item--md {
  height: 26px;
  padding: 0 12px;
  font-size: 12px;
}

.seg__item--sm {
  height: 22px;
  padding: 0 9px;
  font-size: 11px;
}

.seg__item:hover {
  color: var(--t2);
}

.seg__item--active {
  background: var(--panel-2);
  color: var(--gold);
}
</style>
