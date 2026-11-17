<template>
  <label class="switch-field" :class="{ 'switch-field--disabled': disabled }">
    <SwitchRoot
      :model-value="modelValue"
      :disabled="disabled"
      class="switch"
      @update:model-value="emit('update:modelValue', $event)"
    >
      <SwitchThumb class="switch__thumb" />
    </SwitchRoot>
    <span v-if="label || $slots.default" class="switch-field__label">
      <slot>{{ label }}</slot>
    </span>
  </label>
</template>

<script setup lang="ts">
import { SwitchRoot, SwitchThumb } from 'reka-ui'

withDefaults(
  defineProps<{ modelValue?: boolean; label?: string; disabled?: boolean }>(),
  { modelValue: false, label: '', disabled: false }
)

const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()
</script>

<style scoped>
.switch-field {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.switch {
  position: relative;
  display: inline-flex;
  align-items: center;
  width: 32px;
  height: 18px;
  padding: 2px;
  border-radius: 999px;
  border: 1px solid var(--line-strong);
  background: var(--bg);
  transition: background-color var(--d-base) var(--ease-out),
    border-color var(--d-base) var(--ease-out);
  flex: none;
}

.switch[data-state='checked'] {
  background: var(--gold);
  border-color: var(--gold);
}

.switch__thumb {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--t2);
  transition: transform var(--d-base) var(--ease-out),
    background-color var(--d-base) var(--ease-out);
  will-change: transform;
}

.switch[data-state='checked'] .switch__thumb {
  transform: translateX(14px);
  background: var(--gold-ink);
}

.switch-field__label {
  font-size: 13px;
  color: var(--t2);
}

.switch-field--disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>
