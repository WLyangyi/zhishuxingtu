<template>
  <div class="typewriter-text">
    <span class="text-content" v-html="formattedContent"></span>
    <span v-if="isStreaming" class="cursor">|</span>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'

const props = defineProps<{
  content: string
  isStreaming?: boolean
}>()

const formattedContent = computed(() => {
  return props.content
    .replace(/\n/g, '<br>')
    .replace(/【([^】]+)】/g, '<strong>【$1】</strong>')
})
</script>

<style scoped lang="scss">
.typewriter-text {
  display: inline;
}

.text-content {
  white-space: pre-wrap;
  word-break: break-word;
}

.cursor {
  animation: blink 1s infinite;
  font-weight: 100;
  color: var(--primary-color);
}

@keyframes blink {
  0%, 50% {
    opacity: 1;
  }
  51%, 100% {
    opacity: 0;
  }
}
</style>
