<template>
  <AppInput
    :model-value="modelValue"
    :placeholder="placeholder"
    :disabled="disabled"
    type="search"
    @update:model-value="emit('update:modelValue', $event)"
    @enter="emit('search', String(modelValue ?? ''))"
  >
    <template #prefix>
      <Search :size="14" :stroke-width="1.8" />
    </template>
    <template #suffix>
      <button
        v-if="modelValue"
        type="button"
        class="search-clear"
        aria-label="清空搜索"
        @click="clear"
      >
        <X :size="13" :stroke-width="1.8" />
      </button>
    </template>
  </AppInput>
</template>

<script setup lang="ts">
import { Search, X } from 'lucide-vue-next'
import AppInput from './AppInput.vue'

withDefaults(
  defineProps<{ modelValue?: string; placeholder?: string; disabled?: boolean }>(),
  { modelValue: '', placeholder: '搜索', disabled: false }
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
  search: [value: string]
}>()

function clear() {
  emit('update:modelValue', '')
  emit('search', '')
}
</script>

<style scoped>
.search-clear {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: var(--r-sm);
  color: var(--t3);
}

.search-clear:hover {
  color: var(--text);
  background: var(--panel-2);
}
</style>
