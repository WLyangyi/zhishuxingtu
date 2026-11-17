<template>
  <TabsRoot
    :model-value="modelValue"
    class="tabs"
    @update:model-value="emit('update:modelValue', String($event))"
  >
    <TabsList class="tabs__list" :aria-label="ariaLabel">
      <TabsTrigger
        v-for="item in items"
        :key="item.value"
        :value="item.value"
        class="tabs__trigger"
      >
        <component :is="item.icon" v-if="item.icon" class="tabs__icon" />
        <span>{{ item.label }}</span>
        <span v-if="item.count !== undefined" class="tabs__count">{{ item.count }}</span>
      </TabsTrigger>
    </TabsList>

    <div class="tabs__body">
      <slot :active="modelValue" />
    </div>
  </TabsRoot>
</template>

<script setup lang="ts">
import { TabsList, TabsRoot, TabsTrigger } from 'reka-ui'
import type { Component } from 'vue'

export interface TabItem {
  value: string
  label: string
  count?: number
  icon?: Component
}

withDefaults(
  defineProps<{ items: TabItem[]; modelValue?: string; ariaLabel?: string }>(),
  { modelValue: '', ariaLabel: '标签页' }
)

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
</script>

<style scoped>
.tabs {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.tabs__list {
  display: flex;
  align-items: center;
  gap: 20px;
  border-bottom: 1px solid var(--line);
}

.tabs__trigger {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 0 10px;
  font-size: 13px;
  font-weight: 500;
  color: var(--t3);
  transition: color var(--d-fast) var(--ease-out);
}

.tabs__trigger::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 1px;
  background: transparent;
  transition: background-color var(--d-fast) var(--ease-out);
}

.tabs__trigger:hover {
  color: var(--t2);
}

.tabs__trigger[data-state='active'] {
  color: var(--gold);
}

.tabs__trigger[data-state='active']::after {
  background: var(--gold);
}

.tabs__icon {
  width: 14px;
  height: 14px;
}

.tabs__count {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--t3);
}

.tabs__body {
  min-width: 0;
}
</style>
