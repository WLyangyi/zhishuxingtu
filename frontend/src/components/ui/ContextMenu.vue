<template>
  <ContextMenuRoot>
    <ContextMenuTrigger as-child>
      <slot />
    </ContextMenuTrigger>
    <ContextMenuPortal>
      <ContextMenuContent class="zs-context">
        <template v-for="item in items" :key="item.value || item.label">
          <ContextMenuSeparator v-if="item.separator" class="zs-context__separator" />
          <ContextMenuItem
            v-else
            :disabled="item.disabled"
            :class="['zs-context__item', item.danger && 'zs-context__item--danger']"
            @select="emit('select', item.value)"
          >
            <component :is="item.icon" v-if="item.icon" class="zs-context__icon" />
            <span class="zs-context__label">{{ item.label }}</span>
            <Kbd v-if="item.shortcut" :keys="item.shortcut" class="zs-context__kbd" />
          </ContextMenuItem>
        </template>
      </ContextMenuContent>
    </ContextMenuPortal>
  </ContextMenuRoot>
</template>

<script setup lang="ts">
import {
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuPortal,
  ContextMenuRoot,
  ContextMenuSeparator,
  ContextMenuTrigger
} from 'reka-ui'
import type { Component } from 'vue'
import Kbd from './Kbd.vue'

export interface ContextMenuEntry {
  value?: string
  label: string
  icon?: Component
  shortcut?: string
  danger?: boolean
  disabled?: boolean
  separator?: boolean
}

defineProps<{ items: ContextMenuEntry[] }>()
const emit = defineEmits<{ select: [value: string | undefined] }>()
</script>

<style>
.zs-context {
  z-index: var(--z-toast);
  min-width: 180px;
  padding: 4px;
  background: var(--panel);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-md);
  box-shadow: var(--shadow-float);
  animation: zs-context-in 140ms var(--ease-out);
}

.zs-context__item {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 30px;
  padding: 0 8px;
  border-radius: var(--r-sm);
  font-size: 12px;
  color: var(--t2);
  cursor: pointer;
  outline: none;
  user-select: none;
}

.zs-context__item[data-highlighted] {
  background: var(--panel-2);
  color: var(--gold);
}

.zs-context__item[data-disabled] {
  opacity: 0.4;
  pointer-events: none;
}

.zs-context__item--danger {
  color: var(--danger);
}

.zs-context__item--danger[data-highlighted] {
  background: var(--danger-soft);
  color: var(--danger);
}

.zs-context__icon {
  width: 14px;
  height: 14px;
}

.zs-context__label {
  flex: 1;
}

.zs-context__kbd {
  color: var(--t3);
}

.zs-context__separator {
  height: 1px;
  margin: 4px 6px;
  background: var(--line);
}

@keyframes zs-context-in {
  from { opacity: 0; transform: translateY(-2px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
