<template>
  <button
    :type="type"
    :disabled="disabled || loading"
    :aria-busy="loading || undefined"
    :class="classes"
    @click="handleClick"
  >
    <Spinner v-if="loading" :size="size === 'lg' ? 16 : 14" />
    <span v-else-if="$slots.icon" class="btn-icon"><slot name="icon" /></span>
    <span v-if="$slots.default" class="btn-label"><slot /></span>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Spinner from './Spinner.vue'
import { cn } from '@/lib/cn'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'link'
type Size = 'sm' | 'md' | 'lg'

const props = withDefaults(
  defineProps<{
    variant?: Variant
    size?: Size
    type?: 'button' | 'submit' | 'reset'
    loading?: boolean
    disabled?: boolean
    block?: boolean
  }>(),
  {
    variant: 'primary',
    size: 'md',
    type: 'button',
    loading: false,
    disabled: false,
    block: false
  }
)

const emit = defineEmits<{ click: [event: MouseEvent] }>()

const variants: Record<Variant, string> = {
  primary:
    'bg-gold text-gold-ink hover:bg-gold-deep hover:-translate-y-px active:translate-y-0',
  secondary:
    'border border-line-strong text-t2 hover:text-ink hover:bg-panel-2',
  ghost: 'text-t3 hover:text-ink hover:bg-panel-2',
  danger: 'border border-danger-line text-danger hover:bg-danger-soft',
  link: 'px-0 text-gold hover:text-gold-deep underline-offset-4 hover:underline'
}

const sizes: Record<Size, string> = {
  sm: 'h-8 px-3 text-[13px]',
  md: 'h-9 px-4 text-[13px]',
  lg: 'h-11 px-5 text-sm'
}

const classes = computed(() =>
  cn(
    'inline-flex items-center justify-center gap-2 rounded-md font-medium whitespace-nowrap',
    'transition-[background-color,color,border-color,transform] duration-base ease-out select-none',
    variants[props.variant],
    props.variant !== 'link' && sizes[props.size],
    props.block && 'w-full',
    (props.disabled || props.loading) && 'opacity-40 cursor-not-allowed pointer-events-none'
  )
)

function handleClick(event: MouseEvent) {
  if (props.disabled || props.loading) return
  emit('click', event)
}
</script>

<style scoped>
.btn-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn-icon :deep(svg) {
  width: 16px;
  height: 16px;
}

.btn-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
</style>
