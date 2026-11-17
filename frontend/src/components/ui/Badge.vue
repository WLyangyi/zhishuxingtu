<template>
  <span :class="classes">
    <span v-if="dot" class="badge-dot" />
    <slot />
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/cn'

type Tone = 'gold' | 'steel' | 'sage' | 'neutral' | 'danger' | 'success'

const props = withDefaults(
  defineProps<{ tone?: Tone; variant?: 'soft' | 'solid'; dot?: boolean }>(),
  { tone: 'gold', variant: 'soft', dot: false }
)

const tones: Record<Tone, { soft: string; solid: string; dot: string }> = {
  gold: { soft: 'bg-gold-soft text-gold', solid: 'bg-gold text-gold-ink', dot: 'bg-gold' },
  steel: { soft: 'bg-steel-soft text-steel', solid: 'bg-steel text-gold-ink', dot: 'bg-steel' },
  sage: { soft: 'bg-sage-soft text-sage', solid: 'bg-sage text-gold-ink', dot: 'bg-sage' },
  neutral: { soft: 'bg-panel-2 text-t2', solid: 'bg-t3 text-bg', dot: 'bg-t3' },
  danger: { soft: 'bg-danger-soft text-danger', solid: 'bg-danger text-gold-ink', dot: 'bg-danger' },
  success: { soft: 'bg-success-soft text-success', solid: 'bg-success text-gold-ink', dot: 'bg-success' }
}

const classes = computed(() => {
  const tone = tones[props.tone]
  return cn(
    'inline-flex items-center gap-1.5 rounded-sm px-2 py-0.5 text-[11px] font-medium leading-5',
    props.variant === 'solid' ? tone.solid : tone.soft
  )
})
</script>

<style scoped>
.badge-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: currentColor;
}
</style>
