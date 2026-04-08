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
  background: var(--bg-primary);
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
