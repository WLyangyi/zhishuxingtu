<template>
  <div class="main-layout">
    <Header />
    <div class="main-content">
      <main class="content-area">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useFoldersStore } from '@/stores/folders'
import { useTagsStore } from '@/stores/tags'
import { useNotesStore } from '@/stores/notes'
import Header from './Header.vue'

const authStore = useAuthStore()
const foldersStore = useFoldersStore()
const tagsStore = useTagsStore()
const notesStore = useNotesStore()

onMounted(async () => {
  await authStore.fetchUser()
  await foldersStore.fetchFolders()
  await tagsStore.fetchTags()
  await notesStore.fetchNotes()
})
</script>

<style scoped lang="scss">
.main-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: linear-gradient(135deg, #0a0a14 0%, #0d0d1a 50%, #0a0a14 100%);
  transition: background 0.3s ease;
}

:global(body.light) .main-layout {
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 50%, #f8fafc 100%);
}

.main-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.content-area {
  flex: 1;
  overflow-y: auto;
  background: transparent;
}
</style>
