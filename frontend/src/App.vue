<template>
  <div class="app">
    <router-view />
    <Toast />
    <ImportModal />
    <ImportResult />
  </div>
</template>

<script setup lang="ts">
import Toast from '@/components/common/Toast.vue'
import ImportModal from '@/views/ImportModal.vue'
import ImportResult from '@/views/ImportResult.vue'
</script>

<style scoped>
.app {
  min-height: 100vh;
  background: var(--bg);
  color: var(--text);
}
</style>
