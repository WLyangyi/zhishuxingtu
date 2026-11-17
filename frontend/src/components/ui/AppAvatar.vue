<template>
  <span class="avatar" :class="`avatar--${size}`" :title="name">
    <img v-if="src && !imageFailed" :src="src" :alt="name" @error="imageFailed = true" />
    <span v-else class="avatar__initials">{{ initials }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

const props = withDefaults(
  defineProps<{ name?: string; src?: string; size?: 'sm' | 'md' | 'lg' }>(),
  { name: '', src: '', size: 'md' }
)

const imageFailed = ref(false)

const initials = computed(() => {
  const name = props.name.trim()
  if (!name) return '·'
  return name.slice(0, 1).toUpperCase()
})
</script>

<style scoped>
.avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 50%;
  border: 1px solid var(--line-strong);
  background: var(--panel-2);
  color: var(--text);
  font-family: var(--font-display);
  font-weight: 500;
  flex: none;
}

.avatar--sm { width: 24px; height: 24px; font-size: 10px; }
.avatar--md { width: 32px; height: 32px; font-size: 12px; }
.avatar--lg { width: 40px; height: 40px; font-size: 14px; }

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar__initials {
  line-height: 1;
}
</style>
