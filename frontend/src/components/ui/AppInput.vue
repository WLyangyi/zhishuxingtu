<template>
  <label class="field" :class="{ 'field--invalid': invalid, 'field--disabled': disabled }">
    <span v-if="label" class="field__label">
      {{ label }}
      <span v-if="required" class="field__required" aria-hidden="true">*</span>
    </span>

    <span class="field__control">
      <span v-if="$slots.prefix" class="field__affix"><slot name="prefix" /></span>
      <input
        :id="inputId"
        :value="modelValue"
        :type="type"
        :name="name"
        :autocomplete="autocomplete"
        :placeholder="placeholder"
        :disabled="disabled"
        :readonly="readonly"
        :required="required"
        :aria-invalid="invalid || undefined"
        :aria-describedby="hint ? `${inputId}-hint` : undefined"
        class="field__input"
        @input="onInput"
        @keydown.enter="emit('enter', ($event as KeyboardEvent))"
      />
      <span v-if="$slots.suffix" class="field__affix"><slot name="suffix" /></span>
    </span>

    <span v-if="error" class="field__error">{{ error }}</span>
    <span v-else-if="hint" :id="`${inputId}-hint`" class="field__hint">{{ hint }}</span>
  </label>
</template>

<script setup lang="ts">
import { useId } from 'vue'

withDefaults(
  defineProps<{
    modelValue?: string | number
    label?: string
    type?: string
    name?: string
    autocomplete?: string
    placeholder?: string
    disabled?: boolean
    readonly?: boolean
    required?: boolean
    invalid?: boolean
    error?: string
    hint?: string
  }>(),
  {
    modelValue: '',
    type: 'text',
    name: '',
    autocomplete: 'off',
    placeholder: '',
    disabled: false,
    readonly: false,
    required: false,
    invalid: false,
    error: '',
    hint: ''
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
  enter: [event: KeyboardEvent]
}>()

const inputId = useId()

function onInput(event: Event) {
  emit('update:modelValue', (event.target as HTMLInputElement).value)
}
</script>

<style scoped>
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.field__label {
  font-size: 12px;
  font-weight: 500;
  color: var(--t2);
}

.field__required {
  color: var(--gold);
}

.field__control {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 36px;
  padding: 0 10px;
  background: var(--bg);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-md);
  transition: border-color var(--d-fast) var(--ease-out),
    box-shadow var(--d-fast) var(--ease-out);
}

.field__control:focus-within {
  border-color: var(--gold);
  box-shadow: 0 0 0 3px var(--gold-soft);
}

.field__input {
  flex: 1;
  min-width: 0;
  height: 100%;
  border: 0;
  outline: none;
  background: transparent;
  font-size: 13px;
  color: var(--text);
}

.field__input::placeholder {
  color: var(--t3);
}

.field__input:disabled {
  cursor: not-allowed;
}

.field__affix {
  display: inline-flex;
  align-items: center;
  color: var(--t3);
}

.field__affix :deep(svg) {
  width: 14px;
  height: 14px;
}

.field__hint {
  font-size: 11px;
  color: var(--t3);
}

.field__error {
  font-size: 11px;
  color: var(--danger);
}

.field--invalid .field__control {
  border-color: var(--danger);
}

.field--invalid .field__control:focus-within {
  box-shadow: 0 0 0 3px var(--danger-soft);
}

.field--disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>
