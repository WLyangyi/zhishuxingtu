<template>
  <span :class="classes">
    <slot />
    <button
      v-if="closable"
      type="button"
      class="tag-close"
      :aria-label="`移除 ${String($slots.default?.()?.[0]?.children ?? '标签')}`"
      @click.stop="emit('close')"
    >
      ×
    </button>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/cn'

type Tone = 'gold' | 'steel' | 'sage' | 'neutral' | 'danger'

const props = withDefaults(
  defineProps<{ tone?: Tone; closable?: boolean; active?: boolean }>(),
  { tone: 'neutral', closable: false, active: false }
)

const emit = defineEmits<{ close: [] }>()

const tones: Record<Tone, string> = {
  gold: 'border-gold-line text-gold',
  steel: 'border-steel-line text-steel',
  sage: 'border-sage-line text-sage',
  neutral: 'border-line-strong text-t2',
  danger: 'border-danger-line text-danger'
}

const classes = computed(() =>
  cn(
    'inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 text-[12px] leading-5',
    'transition-colors duration-fast ease-out',
    tones[props.tone],
    props.active && 'bg-gold-soft border-gold text-gold',
    props.closable && 'pr-1'
  )
)
</script>

<style scoped>
.tag-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  border-radius: var(--r-sm);
  color: var(--t3);
  font-size: 13px;
  line-height: 1;
}

.tag-close:hover {
  color: var(--text);
  background: var(--panel-2);
}
</style>
