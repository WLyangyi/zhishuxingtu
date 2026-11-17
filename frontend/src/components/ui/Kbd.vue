<template>
  <span class="kbd-group">
    <template v-if="keyList.length">
      <kbd v-for="(key, index) in keyList" :key="index" class="kbd">{{ key }}</kbd>
    </template>
    <kbd v-else class="kbd"><slot /></kbd>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{ keys?: string | string[] }>(), { keys: '' })

const keyList = computed(() => {
  if (Array.isArray(props.keys)) return props.keys
  return props.keys ? props.keys.split(/\s+/) : []
})
</script>

<style scoped>
.kbd-group {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.kbd {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  font-family: var(--font-mono);
  font-size: 10px;
  line-height: 1;
  color: var(--t3);
  background: var(--panel-2);
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
}
</style>
