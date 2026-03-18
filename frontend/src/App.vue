<template>
  <div class="app" :class="{ 'dark': themeStore.isDark }">
    <router-view />
    <Toast />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import Toast from '@/components/common/Toast.vue'
import { useThemeStore } from '@/stores/theme'

const themeStore = useThemeStore()

onMounted(() => {
  themeStore.init()
})
</script>

<style scoped>
.app {
  min-height: 100vh;
  background-color: #f8f9fa;
}

.app.dark {
  background-color: #0f0f1a;
  color: #e5e5e5;
}
</style>
