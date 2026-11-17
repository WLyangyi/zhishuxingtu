<template>
  <div class="select-field">
    <span v-if="label" class="select-field__label">{{ label }}</span>
    <SelectRoot
      :model-value="modelValue"
      :disabled="disabled"
      @update:model-value="emit('update:modelValue', String($event))"
    >
      <SelectTrigger class="select-trigger" :aria-label="label || placeholder">
        <SelectValue :placeholder="placeholder" />
        <SelectIcon class="select-icon">
          <ChevronDown :size="14" :stroke-width="1.8" />
        </SelectIcon>
      </SelectTrigger>

      <SelectPortal>
        <SelectContent class="select-content" position="popper" :side-offset="4">
          <SelectViewport>
            <SelectItem
              v-for="option in options"
              :key="option.value"
              :value="option.value"
              :disabled="option.disabled"
              class="select-item"
            >
              <SelectItemText>{{ option.label }}</SelectItemText>
              <SelectItemIndicator class="select-indicator">✓</SelectItemIndicator>
            </SelectItem>
          </SelectViewport>
        </SelectContent>
      </SelectPortal>
    </SelectRoot>
  </div>
</template>

<script setup lang="ts">
import {
  SelectContent,
  SelectIcon,
  SelectItem,
  SelectItemIndicator,
  SelectItemText,
  SelectPortal,
  SelectRoot,
  SelectTrigger,
  SelectValue,
  SelectViewport
} from 'reka-ui'
import { ChevronDown } from 'lucide-vue-next'

export interface SelectOption {
  label: string
  value: string
  disabled?: boolean
}

withDefaults(
  defineProps<{
    modelValue?: string
    options: SelectOption[]
    label?: string
    placeholder?: string
    disabled?: boolean
  }>(),
  { modelValue: '', label: '', placeholder: '请选择', disabled: false }
)

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
</script>

<style scoped>
.select-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.select-field__label {
  font-size: 12px;
  font-weight: 500;
  color: var(--t2);
}

.select-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  height: 36px;
  padding: 0 10px;
  background: var(--bg);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-md);
  font-size: 13px;
  color: var(--text);
  text-align: left;
  transition: border-color var(--d-fast) var(--ease-out),
    box-shadow var(--d-fast) var(--ease-out);
}

.select-trigger:hover {
  border-color: var(--t3);
}

.select-trigger:focus-visible {
  border-color: var(--gold);
  box-shadow: 0 0 0 3px var(--gold-soft);
}

.select-trigger[data-placeholder] {
  color: var(--t3);
}

.select-icon {
  display: inline-flex;
  color: var(--t3);
}

.select-content {
  z-index: var(--z-overlay);
  min-width: var(--reka-select-trigger-width);
  padding: 4px;
  background: var(--panel);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-md);
  box-shadow: var(--shadow-float);
}

.select-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  height: 30px;
  padding: 0 8px;
  border-radius: var(--r-sm);
  font-size: 13px;
  color: var(--t2);
  cursor: pointer;
  outline: none;
}

.select-item[data-highlighted] {
  background: var(--panel-2);
  color: var(--gold);
}

.select-item[data-disabled] {
  opacity: 0.4;
  cursor: not-allowed;
}

.select-indicator {
  color: var(--gold);
  font-size: 11px;
}
</style>
