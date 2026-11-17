<template>
  <button
    :type="type"
    :aria-label="label"
    :aria-pressed="active || undefined"
    :disabled="disabled"
    :class="classes"
  >
    <slot />
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/cn'

const props = withDefaults(
  defineProps<{
    label: string
    size?: 'sm' | 'md'
    active?: boolean
    disabled?: boolean
    type?: 'button' | 'submit'
  }>(),
  { size: 'md', active: false, disabled: false, type: 'button' }
)

const classes = computed(() =>
  cn(
    'inline-flex items-center justify-center rounded-md text-t3',
    'transition-colors duration-fast ease-out',
    'hover:bg-panel-2 hover:text-ink',
    props.size === 'sm' ? 'h-7 w-7' : 'h-9 w-9',
    props.active && 'bg-panel-2 text-gold',
    props.disabled && 'opacity-40 cursor-not-allowed pointer-events-none'
  )
)
</script>

<style scoped>
button :deep(svg) {
  width: 16px;
  height: 16px;
  stroke-width: 1.8;
}
</style>
