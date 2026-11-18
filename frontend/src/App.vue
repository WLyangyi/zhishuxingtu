<template>
  <div class="app">
    <router-view />
    <AppToast />
    <ImportModal />
    <ImportResult />
  </div>
</template>

<script setup lang="ts">
import AppToast from '@/components/ui/AppToast.vue'
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
