<template>
  <label class="field" :class="{ 'field--invalid': invalid, 'field--disabled': disabled }">
    <span v-if="label" class="field__label">{{ label }}</span>
    <textarea
      :value="modelValue"
      :rows="rows"
      :placeholder="placeholder"
      :disabled="disabled"
      :maxlength="maxlength"
      :aria-invalid="invalid || undefined"
      class="field__textarea"
      @input="onInput"
    />
    <span class="field__meta">
      <span v-if="error" class="field__error">{{ error }}</span>
      <span v-else-if="hint" class="field__hint">{{ hint }}</span>
      <span v-if="showCount && maxlength" class="field__count">
        {{ String(modelValue ?? '').length }} / {{ maxlength }}
      </span>
    </span>
  </label>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    modelValue?: string
    label?: string
    placeholder?: string
    rows?: number
    maxlength?: number
    disabled?: boolean
    invalid?: boolean
    error?: string
    hint?: string
    showCount?: boolean
  }>(),
  {
    modelValue: '',
    placeholder: '',
    rows: 4,
    maxlength: undefined,
    disabled: false,
    invalid: false,
    error: '',
    hint: '',
    showCount: false
  }
)

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

function onInput(event: Event) {
  emit('update:modelValue', (event.target as HTMLTextAreaElement).value)
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

.field__textarea {
  width: 100%;
  padding: 10px 12px;
  background: var(--bg);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-md);
  color: var(--text);
  font-size: 13px;
  line-height: 1.7;
  resize: vertical;
  outline: none;
  transition: border-color var(--d-fast) var(--ease-out),
    box-shadow var(--d-fast) var(--ease-out);
}

.field__textarea::placeholder {
  color: var(--t3);
}

.field__textarea:focus {
  border-color: var(--gold);
  box-shadow: 0 0 0 3px var(--gold-soft);
}

.field__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 14px;
}

.field__hint { font-size: 11px; color: var(--t3); }
.field__error { font-size: 11px; color: var(--danger); }
.field__count {
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--t3);
}

.field--invalid .field__textarea {
  border-color: var(--danger);
}

.field--disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>
