<template>
  <TooltipProvider :delay-duration="delay">
    <TooltipRoot>
      <TooltipTrigger as-child>
        <slot />
      </TooltipTrigger>
      <TooltipPortal>
        <TooltipContent class="zs-tooltip" :side="side" :side-offset="6">
          <span>{{ content }}</span>
          <Kbd v-if="shortcut" :keys="shortcut" class="zs-tooltip__kbd" />
          <TooltipArrow class="zs-tooltip__arrow" />
        </TooltipContent>
      </TooltipPortal>
    </TooltipRoot>
  </TooltipProvider>
</template>

<script setup lang="ts">
import { TooltipArrow, TooltipContent, TooltipPortal, TooltipProvider, TooltipRoot, TooltipTrigger } from 'reka-ui'
import Kbd from './Kbd.vue'

withDefaults(
  defineProps<{ content: string; shortcut?: string; side?: 'top' | 'right' | 'bottom' | 'left'; delay?: number }>(),
  { shortcut: '', side: 'top', delay: 260 }
)
</script>

<style>
.zs-tooltip {
  z-index: var(--z-toast);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 5px 8px;
  background: var(--panel);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-sm);
  box-shadow: var(--shadow-float);
  font-size: 11px;
  color: var(--t2);
  white-space: nowrap;
  animation: zs-tooltip-in 140ms var(--ease-out);
}

.zs-tooltip__kbd {
  color: var(--t3);
}

.zs-tooltip__arrow {
  fill: var(--panel);
  stroke: var(--line-strong);
}

@keyframes zs-tooltip-in {
  from { opacity: 0; transform: translateY(2px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
