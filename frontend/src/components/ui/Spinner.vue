<template>
  <span
    class="spinner"
    :style="{ width: `${size}px`, height: `${size}px` }"
    role="status"
    aria-label="加载中"
  />
</template>

<script setup lang="ts">
withDefaults(defineProps<{ size?: number }>(), { size: 14 })
</script>

<style scoped>
.spinner {
  display: inline-block;
  border: 1.5px solid var(--line-strong);
  border-top-color: var(--gold);
  border-radius: 50%;
  animation: spinner-rotate 700ms linear infinite;
  flex: none;
}

@keyframes spinner-rotate {
  to {
    transform: rotate(360deg);
  }
}
</style>
