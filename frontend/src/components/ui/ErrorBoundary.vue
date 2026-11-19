<template>
  <div v-if="error" class="error-boundary" data-error-boundary>
    <EmptyState title="此区域加载失败" description="该区域暂时无法显示，其他功能仍可正常使用。">
      <AppButton variant="secondary" size="sm" @click="retry">重试</AppButton>
    </EmptyState>
  </div>
  <slot v-else />
</template>

<script setup lang="ts">
import { onErrorCaptured, ref } from 'vue'
import EmptyState from './EmptyState.vue'
import AppButton from './AppButton.vue'

const error = ref<unknown>(null)

onErrorCaptured((err) => {
  error.value = err
  return false
})

function retry() {
  error.value = null
}
</script>

<style scoped>
.error-boundary {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px dashed var(--line);
  border-radius: 8px;
}
</style>
